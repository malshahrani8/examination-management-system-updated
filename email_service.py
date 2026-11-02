from flask import render_template, current_app

try:
    from flask_mail import Mail, Message
    MAIL_AVAILABLE = True
    mail = Mail()
except ImportError:
    MAIL_AVAILABLE = False
    
    class Mail:
        def init_app(self, app):
            pass
        def send(self, msg):
            raise Exception("Flask-Mail غير مثبتة")
    
    class Message:
        def __init__(self, *args, **kwargs):
            pass
    
    mail = Mail()


def send_confirmation_email(trainee, session):
    if not MAIL_AVAILABLE:
        return False, 'خدمة البريد غير متوفرة'
    
    try:
        mail_username = current_app.config.get('MAIL_USERNAME')
        if not mail_username:
            return False, 'إعدادات البريد غير مكتملة'
        
        msg = Message(
            subject='تأكيد التسجيل في الاختبار - TVTC',
            recipients=[trainee.email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        msg.body = f"""
مرحباً {trainee.full_name}،

تم تأكيد تسجيلك بنجاح في اختبار مقرر "{session.course_name}".

📅 تاريخ الجلسة: {session.session_date.strftime('%Y-%m-%d')}
⏰ وقت الجلسة: {session.session_time.strftime('%H:%M')}
🏢 رقم المعمل: {session.location}
🔢 الرقم التدريبي: {trainee.trainee_id}
📚 التخصص: {trainee.specialization}

نتمنى لك التوفيق.
نظام إدارة الاختبارات - TVTC
        """
        
        mail.send(msg)
        return True, 'تم إرسال بريد التأكيد بنجاح'
        
    except Exception as e:
        error_msg = f'فشل إرسال البريد: {str(e)}'
        print(f"⚠️ {error_msg}")
        return False, error_msg