from flask import (Flask, render_template, request, redirect, url_for, 
                   flash, send_file, Response, jsonify, make_response)
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, Admin, Trainee, TestSession, CourseEnrollment, Grade, SPECIALIZATIONS, COURSES, LOCATIONS
from forms import (LoginForm, TraineeRegistrationForm, SessionForm, 
                   CourseEnrollmentUploadForm, GradeForm, TraineeSearchForm)
from email_service import mail, send_confirmation_email
from csv_export import generate_session_report_csv
from csv_importer import import_course_enrollments_from_csv
from config import Config
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs('uploads', exist_ok=True)
os.makedirs('static/img', exist_ok=True)

db.init_app(app)

try:
    from email_service import MAIL_AVAILABLE
    if MAIL_AVAILABLE and app.config.get('MAIL_USERNAME'):
        mail.init_app(app)
except Exception:
    pass

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'الرجاء تسجيل الدخول'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# ═══════════════════════════════════════════════════════
# دوال مساعدة
# ═══════════════════════════════════════════════════════

def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(
                username='admin',
                email='admin@tvtc.gov.sa',
                full_name='مسؤول النظام'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ تم إنشاء حساب مسؤول (admin / admin123)")


def check_time_location_conflict(session_date, session_time, location, exclude_id=None):
    conflict = TestSession.query.filter(
        TestSession.session_date == session_date,
        TestSession.session_time == session_time,
        TestSession.location == location
    )
    if exclude_id:
        conflict = conflict.filter(TestSession.id != exclude_id)
    conflicting_session = conflict.first()
    if conflicting_session:
        return True, conflicting_session
    return False, None


def check_session_time(session):
    session_datetime = datetime.combine(session.session_date, session.session_time)
    server_now = datetime.now()
    time_diff = session_datetime - server_now
    ten_minutes = timedelta(minutes=10)
    
    if time_diff < ten_minutes:
        return False, 'لا يمكن التسجيل، فات وقت التسجيل في الجلسة.'
    return True, 'التسجيل مسموح'


def check_registration_rules(trainee_id, session_id, course_name):
    enrollment = CourseEnrollment.query.filter_by(
        trainee_id=trainee_id, course_name=course_name
    ).first()
    
    if not enrollment:
        return False, 'عذراً، أنت غير مسجل في هذا المقرر'
    
    trainee_registrations = Trainee.query.filter_by(trainee_id=trainee_id).join(TestSession).filter(
        TestSession.course_name == course_name
    ).all()
    
    if len(trainee_registrations) >= 3:
        return False, 'لقد وصلت للحد الأقصى (3 جلسات)'
    
    for reg in trainee_registrations:
        if reg.session_id == int(session_id):
            return False, 'أنت مسجل بالفعل في هذه الجلسة'
    
    if len(trainee_registrations) > 0:
        sorted_regs = sorted(trainee_registrations, key=lambda x: x.registration_order)
        last_registration = sorted_regs[-1]
        
        if last_registration.attendance_status == 'attended':
            if last_registration.passed:
                return False, f'🎉 لقد اجتزت الاختبار بنجاح (الدرجة: {last_registration.latest_grade.score})'
        elif last_registration.attendance_status == 'missed':
            pass
        else:
            return False, 'لم تُرصد حالة حضورك في الجلسة السابقة بعد'
        
        new_session = TestSession.query.get(session_id)
        for reg in trainee_registrations:
            existing_session = reg.session
            if (existing_session.session_date == new_session.session_date and 
                existing_session.session_time == new_session.session_time):
                return False, 'لا يمكن التسجيل في جلسات متزامنة'
    
    return True, 'التسجيل مسموح'


# ═══════════════════════════════════════════════════════
# المسارات العامة
# ═══════════════════════════════════════════════════════

@app.route('/')
def index():
    form = TraineeRegistrationForm()
    return render_template('index.html', form=form, specializations=SPECIALIZATIONS)


@app.route('/api/sessions')
def api_sessions():
    specialization = request.args.get('specialization')
    course_name = request.args.get('course_name', 'مقدمة تطبيقات الحاسب')
    
    if not specialization:
        return {'sessions': []}
    
    available_sessions = TestSession.query.filter_by(
        specialization=specialization, course_name=course_name
    ).order_by(TestSession.session_date, TestSession.session_time).all()
    
    available_sessions = [s for s in available_sessions if not s.is_full]
    
    sessions_data = []
    for session in available_sessions:
        sessions_data.append({
            'id': session.id,
            'course_name': session.course_name,
            'specialization': session.specialization,
            'session_date': session.session_date.strftime('%Y-%m-%d'),
            'session_time': session.session_time.strftime('%H:%M'),
            'location': session.location,
            'current_count': session.current_count,
            'max_capacity': session.max_capacity,
            'available_seats': session.available_seats
        })
    
    return {'sessions': sessions_data}


@app.route('/api/trainee-info')
def api_trainee_info():
    trainee_id = request.args.get('trainee_id', '').strip()
    course_name = request.args.get('course_name', 'مقدمة تطبيقات الحاسب')
    
    if not trainee_id or len(trainee_id) < 6:
        return jsonify({
            'success': False,
            'message': 'الرجاء إدخال رقم تدريبي صحيح'
        })
    
    enrollment = CourseEnrollment.query.filter_by(
        trainee_id=trainee_id, course_name=course_name
    ).first()
    
    if not enrollment:
        return jsonify({
            'success': False,
            'message': 'الرقم التدريبي غير مسجل في هذا المقرر'
        })
    
    sessions_count = Trainee.query.filter_by(trainee_id=trainee_id).join(TestSession).filter(
        TestSession.course_name == course_name
    ).count()
    
    latest_grade = None
    trainee_records = Trainee.query.filter_by(trainee_id=trainee_id).join(TestSession).filter(
        TestSession.course_name == course_name
    ).all()
    
    for record in trainee_records:
        if record.latest_grade:
            if latest_grade is None or record.latest_grade.graded_at > latest_grade.graded_at:
                latest_grade = record.latest_grade
    
    return jsonify({
        'success': True,
        'message': 'تم العثور على المتدرب',
        'data': {
            'trainee_id': enrollment.trainee_id,
            'full_name': enrollment.full_name,
            'specialization': enrollment.specialization,
            'phone': enrollment.phone or '',
            'email': enrollment.email or '',
            'course_name': enrollment.course_name,
            'sessions_registered': sessions_count,
            'latest_score': latest_grade.score if latest_grade else None,
            'passed': latest_grade.passed if latest_grade else False
        }
    })


@app.route('/api/server-time')
def api_server_time():
    now = datetime.now()
    return {
        'server_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'timestamp': int(now.timestamp())
    }


@app.route('/register', methods=['POST'])
def register():
    form = TraineeRegistrationForm(request.form)
    
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, 'danger')
        return redirect(url_for('index'))
    
    if not form.declaration.data:
        flash('يجب الموافقة على الإقرار والتعهد', 'danger')
        return redirect(url_for('index'))
    
    if not form.acknowledge_instructions.data:
        flash('يجب الإقرار بالاطلاع على تعليمات الاختبار', 'danger')
        return redirect(url_for('index'))
    
    try:
        trainee_id = form.trainee_id.data.strip()
        email = form.email.data.strip().lower() if form.email.data else None
        phone = form.phone.data.strip() if form.phone.data else None
        full_name = form.full_name.data.strip()
        specialization = form.specialization.data
        session_id = form.session_id.data
        
        session = TestSession.query.get(session_id)
        
        if not session or session.is_full:
            flash('الجلسة غير متاحة', 'danger')
            return redirect(url_for('index'))
        
        # التحقق الزمني
        is_time_allowed, time_message = check_session_time(session)
        if not is_time_allowed:
            flash(time_message, 'danger')
            return redirect(url_for('index'))
        
        is_allowed, message = check_registration_rules(trainee_id, session_id, session.course_name)
        if not is_allowed:
            flash(message, 'danger')
            return redirect(url_for('index'))
        
        existing_count = Trainee.query.filter_by(trainee_id=trainee_id).join(TestSession).filter(
            TestSession.course_name == session.course_name
        ).count()
        registration_order = existing_count + 1
        
        session = db.session.query(TestSession).filter_by(id=session_id).with_for_update().first()
        
        if session.is_full:
            flash('اكتملت الجلسة', 'danger')
            return redirect(url_for('index'))
        
        new_trainee = Trainee(
            full_name=full_name,
            email=email,
            phone=phone,
            trainee_id=trainee_id,
            specialization=specialization,
            session_id=session_id,
            registration_order=registration_order,
            attendance_status='pending',
            acknowledged_instructions=True
        )
        
        db.session.add(new_trainee)
        db.session.commit()
        
        email_sent, email_msg = send_confirmation_email(new_trainee, session)
        
        return render_template('success.html',
                             trainee=new_trainee,
                             session=session,
                             email_sent=email_sent)
        
    except IntegrityError:
        db.session.rollback()
        flash('الرقم التدريبي مسجل مسبقاً في هذه الجلسة', 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'خطأ: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/print-acknowledgment/<int:trainee_id>')
def print_acknowledgment(trainee_id):
    trainee = Trainee.query.get_or_404(trainee_id)
    session = trainee.session
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>إقرار المتدرب - {trainee.full_name}</title>
        <style>
            body {{ font-family: 'Tajawal', Arial; padding: 40px; direction: rtl; }}
            .header {{ text-align: center; border-bottom: 4px solid #2563eb; padding-bottom: 20px; }}
            .info-box {{ background: #f0f9ff; border: 2px solid #2563eb; padding: 20px; margin: 20px 0; border-radius: 10px; }}
            .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #ccc; }}
            .acknowledgment-box {{ background: #fef3c7; border: 2px solid #f59e0b; padding: 25px; margin: 30px 0; border-radius: 10px; }}
            .signature-section {{ margin-top: 60px; display: flex; justify-content: space-between; }}
            .signature-box {{ text-align: center; width: 45%; }}
            .signature-line {{ border-top: 2px solid #333; margin-top: 60px; padding-top: 10px; }}
            .print-btn {{ position: fixed; top: 20px; left: 20px; background: #2563eb; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; }}
            @media print {{ .print-btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <button class="print-btn" onclick="window.print()">🖨️ طباعة</button>
        <div class="header">
            <h1>نظام إدارة الاختبارات</h1>
            <h2>إقرار المتدرب بالاطلاع على تعليمات الاختبار</h2>
        </div>
        <div class="info-box">
            <h3>📋 بيانات المتدرب</h3>
            <div class="info-row"><strong>الاسم:</strong><span>{trainee.full_name}</span></div>
            <div class="info-row"><strong>الرقم التدريبي:</strong><span>{trainee.trainee_id}</span></div>
            <div class="info-row"><strong>التخصص:</strong><span>{trainee.specialization}</span></div>
        </div>
        <div class="info-box">
            <h3>📅 بيانات الجلسة</h3>
            <div class="info-row"><strong>المقرر:</strong><span>{session.course_name}</span></div>
            <div class="info-row"><strong>التاريخ:</strong><span>{session.session_date.strftime('%Y-%m-%d')}</span></div>
            <div class="info-row"><strong>الوقت:</strong><span>{session.session_time.strftime('%H:%M')}</span></div>
            <div class="info-row"><strong>المعمل:</strong><span>{session.location}</span></div>
        </div>
        <div class="acknowledgment-box">
            <h3>✅ الإقرار</h3>
            <p>أقر بأنني اطلعت على كافة تعليمات الاختبار وأتعهد بالالتزام التام بها.</p>
        </div>
        <div class="signature-section">
            <div class="signature-box"><div class="signature-line"><strong>توقيع المتدرب</strong><br>{trainee.full_name}</div></div>
            <div class="signature-box"><div class="signature-line"><strong>التاريخ</strong><br>{datetime.now().strftime('%Y-%m-%d')}</div></div>
        </div>
    </body>
    </html>
    """
    
    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response


# ═══════════════════════════════════════════════════════
# مسارات المسؤول
# ═══════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin)
            flash(f'مرحباً {admin.full_name}!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('بيانات الدخول غير صحيحة', 'danger')
    return render_template('admin/login.html', form=form)


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('تم تسجيل الخروج', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_dashboard():
    sessions = TestSession.query.order_by(TestSession.session_date).all()
    total_trainees = Trainee.query.count()
    total_sessions = len(sessions)
    full_sessions = sum(1 for s in sessions if s.is_full)
    total_enrollments = CourseEnrollment.query.count()
    total_graded = Grade.query.count()
    
    return render_template('admin/dashboard.html',
                         sessions=sessions,
                         total_trainees=total_trainees,
                         total_sessions=total_sessions,
                         full_sessions=full_sessions,
                         total_enrollments=total_enrollments,
                         total_graded=total_graded)


@app.route('/admin/sessions')
@login_required
def admin_sessions():
    sessions = TestSession.query.order_by(
        TestSession.session_date, TestSession.session_time
    ).all()
    return render_template('admin/sessions.html', sessions=sessions)


@app.route('/admin/sessions/new', methods=['GET', 'POST'])
@login_required
def admin_session_new():
    form = SessionForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                session_date = form.session_date.data
                session_time = form.session_time.data
                location = form.location.data
                
                is_conflict, conflicting_session = check_time_location_conflict(
                    session_date, session_time, location
                )
                
                if is_conflict:
                    flash(f'⚠️ المعمل "{conflicting_session.location}" مخصص لجلسة أخرى في هذا الوقت', 'danger')
                    return redirect(url_for('admin_session_new'))
                
                session = TestSession(
                    course_name=form.course_name.data,
                    specialization=form.specialization.data,
                    session_date=session_date,
                    session_time=session_time,
                    location=location,
                    max_capacity=form.max_capacity.data
                )
                db.session.add(session)
                db.session.commit()
                flash('✅ تم إنشاء الجلسة', 'success')
                return redirect(url_for('admin_sessions'))
            except Exception as e:
                db.session.rollback()
                flash(f'❌ خطأ: {str(e)}', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'❌ {error}', 'danger')
    
    return render_template('admin/session_form.html', form=form, title='إضافة جلسة')


@app.route('/admin/sessions/<int:session_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_session_edit(session_id):
    session = TestSession.query.get_or_404(session_id)
    form = SessionForm(obj=session)
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                session_date = form.session_date.data
                session_time = form.session_time.data
                location = form.location.data
                
                is_conflict, conflicting_session = check_time_location_conflict(
                    session_date, session_time, location, exclude_id=session_id
                )
                
                if is_conflict:
                    flash(f'⚠️ المعمل مخصص لجلسة أخرى في هذا الوقت', 'danger')
                    return redirect(url_for('admin_session_edit', session_id=session_id))
                
                session.course_name = form.course_name.data
                session.specialization = form.specialization.data
                session.session_date = session_date
                session.session_time = session_time
                session.location = location
                session.max_capacity = form.max_capacity.data
                db.session.commit()
                flash('✅ تم التحديث', 'success')
                return redirect(url_for('admin_sessions'))
            except Exception as e:
                db.session.rollback()
                flash(f'❌ خطأ: {str(e)}', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'❌ {error}', 'danger')
    
    return render_template('admin/session_form.html', form=form, session=session, title='تعديل جلسة')


@app.route('/admin/sessions/<int:session_id>/delete', methods=['POST'])
@login_required
def admin_session_delete(session_id):
    session = TestSession.query.get_or_404(session_id)
    try:
        db.session.delete(session)
        db.session.commit()
        flash('✅ تم حذف الجلسة', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ خطأ: {str(e)}', 'danger')
    return redirect(url_for('admin_sessions'))


@app.route('/admin/sessions/<int:session_id>/attendance', methods=['GET', 'POST'])
@login_required
def admin_session_attendance(session_id):
    session = TestSession.query.get_or_404(session_id)
    
    if request.method == 'POST':
        for trainee in session.trainees:
            status = request.form.get(f'attendance_{trainee.id}')
            if status:
                trainee.attendance_status = status
        db.session.commit()
        flash('✅ تم تحديث الحضور', 'success')
        return redirect(url_for('admin_session_attendance', session_id=session_id))
    
    return render_template('admin/attendance.html', session=session)


@app.route('/admin/sessions/<int:session_id>/grades', methods=['GET', 'POST'])
@login_required
def admin_session_grades(session_id):
    session = TestSession.query.get_or_404(session_id)
    
    if request.method == 'POST':
        for trainee in session.trainees:
            score_str = request.form.get(f'score_{trainee.id}')
            attempt_str = request.form.get(f'attempt_{trainee.id}', '1')
            notes = request.form.get(f'notes_{trainee.id}', '')
            
            if score_str:
                try:
                    score = float(score_str)
                    attempt = int(attempt_str)
                    
                    existing_grade = Grade.query.filter_by(
                        trainee_id=trainee.id,
                        session_id=session_id,
                        attempt_number=attempt
                    ).first()
                    
                    if existing_grade:
                        existing_grade.score = score
                        existing_grade.notes = notes
                    else:
                        new_grade = Grade(
                            trainee_id=trainee.id,
                            session_id=session_id,
                            score=score,
                            attempt_number=attempt,
                            notes=notes,
                            graded_by=current_user.id
                        )
                        db.session.add(new_grade)
                    
                except ValueError:
                    flash(f'❌ درجة غير صحيحة', 'danger')
        
        db.session.commit()
        flash('✅ تم رصد الدرجات', 'success')
        return redirect(url_for('admin_session_grades', session_id=session_id))
    
    return render_template('admin/grades.html', session=session)


@app.route('/admin/trainee-search', methods=['GET', 'POST'])
@login_required
def admin_trainee_search():
    form = TraineeSearchForm()
    trainee_data = None
    sessions_data = []
    error_message = None
    
    if request.method == 'POST':
        if form.validate_on_submit():
            trainee_id = form.trainee_id.data.strip()
            enrollment = CourseEnrollment.query.filter_by(trainee_id=trainee_id).first()
            
            if not enrollment:
                error_message = f'⚠️ لم يتم العثور على متدرب بالرقم: {trainee_id}'
            else:
                trainee_records = Trainee.query.filter_by(trainee_id=trainee_id).all()
                sessions_data = []
                total_score = 0
                scores_count = 0
                
                for record in trainee_records:
                    session = record.session
                    latest_grade = record.latest_grade
                    
                    session_info = {
                        'session_id': session.id,
                        'course_name': session.course_name,
                        'specialization': session.specialization,
                        'session_date': session.session_date.strftime('%Y-%m-%d'),
                        'session_time': session.session_time.strftime('%H:%M'),
                        'location': session.location,
                        'registration_order': record.registration_order,
                        'attendance_status': record.attendance_status,
                        'registered_at': record.registered_at.strftime('%Y-%m-%d %H:%M'),
                        'grade': latest_grade.score if latest_grade else None,
                        'passed': latest_grade.passed if latest_grade else False,
                        'attempt_number': latest_grade.attempt_number if latest_grade else None,
                        'grade_notes': latest_grade.notes if latest_grade else None
                    }
                    
                    if latest_grade:
                        total_score += latest_grade.score
                        scores_count += 1
                    
                    sessions_data.append(session_info)
                
                avg_score = (total_score / scores_count) if scores_count > 0 else None
                
                trainee_data = {
                    'trainee_id': enrollment.trainee_id,
                    'full_name': enrollment.full_name,
                    'specialization': enrollment.specialization,
                    'phone': enrollment.phone or '-',
                    'email': enrollment.email or '-',
                    'course_name': enrollment.course_name,
                    'enrolled_at': enrollment.enrolled_at.strftime('%Y-%m-%d'),
                    'total_sessions': len(sessions_data),
                    'attended_count': sum(1 for s in sessions_data if s['attendance_status'] == 'attended'),
                    'missed_count': sum(1 for s in sessions_data if s['attendance_status'] == 'missed'),
                    'avg_score': avg_score,
                    'passed_any': any(s['passed'] for s in sessions_data)
                }
    
    return render_template('admin/trainee_search.html',
                         form=form,
                         trainee_data=trainee_data,
                         sessions_data=sessions_data,
                         error_message=error_message)


@app.route('/admin/enrollments')
@login_required
def admin_enrollments():
    course_filter = request.args.get('course', '')
    spec_filter = request.args.get('specialization', '')
    
    query = CourseEnrollment.query
    if course_filter:
        query = query.filter_by(course_name=course_filter)
    if spec_filter:
        query = query.filter_by(specialization=spec_filter)
    
    enrollments = query.order_by(CourseEnrollment.course_name, CourseEnrollment.full_name).all()
    
    return render_template('admin/course_enrollments.html',
                         enrollments=enrollments,
                         courses=COURSES,
                         specializations=SPECIALIZATIONS,
                         current_course=course_filter,
                         current_spec=spec_filter)


@app.route('/admin/enrollments/upload', methods=['GET', 'POST'])
@login_required
def admin_enrollments_upload():
    form = CourseEnrollmentUploadForm()
    
    if form.validate_on_submit():
        course_name = form.course_name.data
        csv_file = form.csv_file.data
        
        results = import_course_enrollments_from_csv(
            csv_file.stream, course_name, current_user.id
        )
        
        if results['success'] > 0:
            flash(f'✅ تم استيراد {results["success"]} متدرب', 'success')
        if results['skipped'] > 0:
            flash(f'⚠️ تم تخطي {results["skipped"]} سجل', 'warning')
        if results['errors']:
            for error in results['errors'][:5]:
                flash(f'❌ {error}', 'danger')
        
        return redirect(url_for('admin_enrollments'))
    
    return render_template('admin/enrollment_upload.html', form=form, courses=COURSES)


@app.route('/admin/enrollments/delete/<int:enrollment_id>', methods=['POST'])
@login_required
def admin_enrollment_delete(enrollment_id):
    enrollment = CourseEnrollment.query.get_or_404(enrollment_id)
    db.session.delete(enrollment)
    db.session.commit()
    flash('تم الحذف', 'success')
    return redirect(url_for('admin_enrollments'))


@app.route('/admin/reports')
@login_required
def admin_reports():
    sessions = TestSession.query.order_by(TestSession.session_date).all()
    return render_template('admin/reports.html', sessions=sessions)


@app.route('/admin/reports/<int:session_id>/csv')
@login_required
def admin_report_csv(session_id):
    session = TestSession.query.get_or_404(session_id)
    csv_content = generate_session_report_csv(session)
    filename = f"report_{session_id}_{session.session_date}.csv"
    
    return Response(
        csv_content,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/admin/reports/<int:session_id>/print')
@login_required
def admin_report_print(session_id):
    session = TestSession.query.get_or_404(session_id)
    return render_template('admin/report_print.html', session=session)


if __name__ == '__main__':
    init_db()
    print("\n" + "="*70)
    print("🎓 نظام إدارة اختبارات TVTC")
    print("="*70)
    print("🌐 http://127.0.0.1:5000")
    print("🔐 http://127.0.0.1:5000/admin/login")
    print("👤 admin / admin123")
    print("="*70 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)