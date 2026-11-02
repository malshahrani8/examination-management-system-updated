import csv
import io
from models import db, CourseEnrollment, CSV_SPECIALIZATION_MAPPING


def import_course_enrollments_from_csv(file_stream, course_name, admin_id):
    results = {
        'success': 0,
        'skipped': 0,
        'errors': [],
        'total': 0
    }
    
    try:
        content = file_stream.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        
        required_fields = ['رقم المتدرب', 'إسم المتدرب', 'التخصص']
        if not reader.fieldnames:
            return {
                'success': 0, 'skipped': 0, 'errors': ['ملف CSV فارغ أو غير صالح'], 'total': 0
            }
        
        fieldnames_clean = {f.strip(): f for f in reader.fieldnames}
        
        for required in required_fields:
            if required not in fieldnames_clean:
                return {
                    'success': 0, 'skipped': 0, 'total': 0,
                    'errors': [f'العمود "{required}" غير موجود في الملف. الأعمدة الموجودة: {", ".join(reader.fieldnames)}']
                }
        
        for row_num, row in enumerate(reader, start=2):
            try:
                results['total'] += 1
                
                trainee_id = row.get('رقم المتدرب', '').strip()
                full_name = row.get('إسم المتدرب', '').strip()
                specialization_raw = row.get('التخصص', '').strip()
                phone = row.get('رقم الجوال', '').strip()
                email = row.get('البريد الإلكتروني', '').strip()
                
                if not trainee_id or not full_name or not specialization_raw:
                    results['errors'].append(f'الصف {row_num}: بيانات ناقصة')
                    results['skipped'] += 1
                    continue
                
                specialization = CSV_SPECIALIZATION_MAPPING.get(
                    specialization_raw, specialization_raw
                )
                
                existing = CourseEnrollment.query.filter_by(
                    trainee_id=trainee_id,
                    course_name=course_name
                ).first()
                
                if existing:
                    results['skipped'] += 1
                    continue
                
                enrollment = CourseEnrollment(
                    trainee_id=trainee_id,
                    full_name=full_name,
                    course_name=course_name,
                    specialization=specialization,
                    phone=phone if phone else None,
                    email=email if email else None,
                    enrolled_by=admin_id
                )
                db.session.add(enrollment)
                results['success'] += 1
                
            except Exception as e:
                results['errors'].append(f'الصف {row_num}: {str(e)}')
                results['skipped'] += 1
        
        db.session.commit()
        
    except UnicodeDecodeError:
        return {
            'success': 0, 'skipped': 0, 'total': 0,
            'errors': ['فشل قراءة الملف. تأكد من أن الترميز UTF-8']
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': 0, 'skipped': 0, 'total': 0,
            'errors': [f'خطأ عام: {str(e)}']
        }
    
    return results