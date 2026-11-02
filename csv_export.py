import csv
import io
from datetime import datetime


def generate_session_report_csv(session):
    output = io.StringIO()
    output.write('\ufeff')
    
    writer = csv.writer(output)
    
    writer.writerow(['المؤسسة العامة للتدريب التقني والمهني - TVTC'])
    writer.writerow([f'تقرير جلسة اختبار - {session.course_name}'])
    writer.writerow([])
    
    writer.writerow(['تاريخ الجلسة:', session.session_date.strftime('%Y-%m-%d')])
    writer.writerow(['وقت الجلسة:', session.session_time.strftime('%H:%M')])
    writer.writerow(['رقم المعمل:', session.location])
    writer.writerow(['التخصص:', session.specialization])
    writer.writerow(['عدد المسجلين:', f'{session.current_count} / {session.max_capacity}'])
    writer.writerow(['تاريخ التقرير:', datetime.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    
    writer.writerow([
        '#',
        'الرقم التدريبي',
        'الاسم الكامل',
        'البريد الإلكتروني',
        'رقم الجوال',
        'التخصص',
        'المحاولة',
        'الحالة',
        'الدرجة',
        'تاريخ التسجيل'
    ])
    
    for idx, trainee in enumerate(session.trainees, 1):
        latest_grade = trainee.latest_grade
        writer.writerow([
            idx,
            trainee.trainee_id,
            trainee.full_name,
            trainee.email or '-',
            trainee.phone or '-',
            trainee.specialization,
            latest_grade.attempt_number if latest_grade else '-',
            'حضر' if trainee.attendance_status == 'attended' else 'لم يحضر',
            latest_grade.score if latest_grade else '-',
            trainee.registered_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    output.seek(0)
    return output.getvalue()