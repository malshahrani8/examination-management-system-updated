from xhtml2pdf import pisa
from flask import render_template_string
from io import BytesIO
from datetime import datetime

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تقرير جلسة الاختبار</title>
    <style>
        body { 
            font-family: 'Arial', 'Tahoma', sans-serif; 
            padding: 20px; 
            direction: rtl;
        }
        .header { 
            text-align: center; 
            border-bottom: 3px solid #00634B; 
            padding-bottom: 20px; 
            margin-bottom: 20px; 
        }
        .header h1 { color: #00634B; margin: 0; font-size: 24px; }
        .header h2 { color: #666; margin: 10px 0; font-size: 16px; }
        .header h3 { color: #00634B; margin: 10px 0; font-size: 18px; }
        
        .info-box { 
            background-color: #E8F3EE; 
            padding: 15px; 
            border: 1px solid #00634B;
            margin-bottom: 20px; 
        }
        .info-box p { margin: 8px 0; font-size: 14px; }
        
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 20px; 
        }
        th { 
            background-color: #00634B; 
            color: white; 
            padding: 10px; 
            text-align: right; 
            font-size: 14px;
        }
        td { 
            padding: 8px; 
            border: 1px solid #ddd; 
            text-align: right; 
            font-size: 13px;
        }
        tr:nth-child(even) { background-color: #f9f9f9; }
        
        .footer { 
            text-align: center; 
            margin-top: 30px; 
            color: #666; 
            font-size: 12px; 
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>المؤسسة العامة للتدريب التقني والمهني</h1>
        <h2>Technical and Vocational Training Corporation - TVTC</h2>
        <h3>تقرير جلسة اختبار - {{ session.course_name }}</h3>
    </div>
    
    <div class="info-box">
        <p><strong>📅 تاريخ الجلسة:</strong> {{ session.session_date.strftime('%Y-%m-%d') }}</p>
        <p><strong>⏰ وقت الجلسة:</strong> {{ session.session_time.strftime('%H:%M') }}</p>
        <p><strong>🏢 رقم المعمل:</strong> {{ session.location }}</p>
        <p><strong>👥 عدد المسجلين:</strong> {{ session.current_count }} / {{ session.max_capacity }}</p>
        <p><strong>📅 تاريخ التقرير:</strong> {{ report_date }}</p>
    </div>
    
    <table>
        <thead>
            <tr>
                <th width="5%">#</th>
                <th width="15%">الرقم التدريبي</th>
                <th width="30%">الاسم الكامل</th>
                <th width="25%">البريد الإلكتروني</th>
                <th width="15%">رقم الجوال</th>
                <th width="10%">تاريخ التسجيل</th>
            </tr>
        </thead>
        <tbody>
            {% for trainee in session.trainees %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ trainee.trainee_id }}</td>
                <td>{{ trainee.full_name }}</td>
                <td>{{ trainee.email }}</td>
                <td>{{ trainee.phone }}</td>
                <td>{{ trainee.registered_at.strftime('%Y-%m-%d %H:%M') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div class="footer">
        <p>تم إنشاء هذا التقرير تلقائياً بواسطة نظام التسجيل الإلكتروني - TVTC</p>
    </div>
</body>
</html>
"""

def generate_session_report_pdf(session):
    """توليد تقرير PDF لجلسة معينة باستخدام xhtml2pdf"""
    html_string = render_template_string(
        REPORT_TEMPLATE,
        session=session,
        report_date=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    
    pdf_file = BytesIO()
    
    # تحويل HTML إلى PDF
    pisa_status = pisa.CreatePDF(
        html_string, 
        dest=pdf_file, 
        encoding='utf-8'
    )
    
    if pisa_status.err:
        raise Exception("فشل في توليد ملف PDF")
        
    pdf_file.seek(0)
    return pdf_file