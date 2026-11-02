from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, DateField, TimeField, 
                     IntegerField, SelectField, BooleanField, SubmitField, 
                     FloatField, TextAreaField)
from wtforms.validators import DataRequired, Email, Length, Regexp, NumberRange, Optional
from models import SPECIALIZATIONS, COURSES, LOCATIONS


class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[
        DataRequired(message='اسم المستخدم مطلوب')
    ])
    password = PasswordField('كلمة المرور', validators=[
        DataRequired(message='كلمة المرور مطلوبة')
    ])
    submit = SubmitField('تسجيل الدخول')


class TraineeRegistrationForm(FlaskForm):
    trainee_id = StringField('الرقم التدريبي', validators=[
        DataRequired(message='الرقم التدريبي مطلوب'),
        Regexp(r'^[0-9]{6,10}$', message='الرقم التدريبي يجب أن يتكون من 6-10 أرقام فقط')
    ])
    
    full_name = StringField('الاسم الكامل', validators=[
        DataRequired(message='الاسم الكامل مطلوب'),
        Length(min=3, max=100, message='يجب أن يكون الاسم بين 3 و 100 حرف')
    ])
    
    phone = StringField('رقم الجوال', validators=[
        Optional(),
        Regexp(r'^05[0-9]{8}$', message='رقم الجوال يجب أن يبدأ بـ 05 ويتكون من 10 أرقام')
    ])
    
    email = StringField('البريد الإلكتروني', validators=[
        Optional(),
        Email(message='صيغة البريد الإلكتروني غير صحيحة')
    ])
    
    specialization = StringField('التخصص', validators=[
        DataRequired(message='يجب تحديد التخصص')
    ])
    
    session_id = StringField('الجلسة المختارة', validators=[
        DataRequired(message='يجب اختيار جلسة')
    ])
    
    declaration = BooleanField('أقر وأتعهد', validators=[
        DataRequired(message='يجب الموافقة على الإقرار والتعهد للمتابعة')
    ])
    
    acknowledge_instructions = BooleanField('أقر بالاطلاع على التعليمات', validators=[
        DataRequired(message='يجب الإقرار بالاطلاع على تعليمات الاختبار')
    ])
    
    submit = SubmitField('تأكيد التسجيل')


class SessionForm(FlaskForm):
    course_name = SelectField('المقرر', choices=COURSES, validators=[
        DataRequired(message='يجب اختيار المقرر')
    ])
    
    specialization = SelectField('التخصص', choices=SPECIALIZATIONS, validators=[
        DataRequired(message='يجب اختيار التخصص')
    ])
    
    session_date = DateField('تاريخ الجلسة', format='%Y-%m-%d',
                             validators=[DataRequired(message='تاريخ الجلسة مطلوب')])
    session_time = TimeField('وقت الجلسة', format='%H:%M',
                             validators=[DataRequired(message='وقت الجلسة مطلوب')])
    
    location = SelectField('المعمل / مكان الجلسة', choices=LOCATIONS, validators=[
        DataRequired(message='يجب اختيار المعمل')
    ])
    
    max_capacity = IntegerField('السعة القصوى', default=20,
                                validators=[
                                    DataRequired(message='السعة مطلوبة'),
                                    NumberRange(min=1, max=50, message='السعة بين 1 و 50')
                                ])
    submit = SubmitField('حفظ')


class CourseEnrollmentUploadForm(FlaskForm):
    course_name = SelectField('المقرر', choices=COURSES, validators=[
        DataRequired(message='يجب اختيار المقرر')
    ])
    csv_file = FileField('ملف CSV', validators=[
        DataRequired(message='يجب اختيار ملف CSV'),
        FileAllowed(['csv'], 'يجب أن يكون الملف بصيغة CSV فقط')
    ])
    submit = SubmitField('رفع البيانات')


class GradeForm(FlaskForm):
    score = FloatField('الدرجة (من 100)', validators=[
        DataRequired(message='الدرجة مطلوبة'),
        NumberRange(min=0, max=100, message='الدرجة يجب أن تكون بين 0 و 100')
    ])
    attempt_number = IntegerField('رقم المحاولة', default=1, validators=[
        DataRequired(message='رقم المحاولة مطلوب'),
        NumberRange(min=1, max=3, message='رقم المحاولة بين 1 و 3')
    ])
    notes = TextAreaField('ملاحظات', validators=[Optional()])
    submit = SubmitField('رصد الدرجة')


class TraineeSearchForm(FlaskForm):
    trainee_id = StringField('الرقم التدريبي', validators=[
        DataRequired(message='الرقم التدريبي مطلوب'),
        Regexp(r'^[0-9]{6,10}$', message='الرقم التدريبي يجب أن يتكون من 6-10 أرقام فقط')
    ])
    submit = SubmitField('بحث')