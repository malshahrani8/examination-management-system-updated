from flask import render_template_string
from datetime import datetime

EXCEL_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal">
   <Alignment ss:Vertical="Center" ss:Horizontal="Right"/>
   <Font ss:FontName="Arial" ss:Size="11"/>
  </Style>
  <Style ss:ID="Header">
   <Alignment ss:Vertical="Center" ss:Horizontal="Center"/>
   <Font ss:FontName="Arial" ss:Size="12" ss:Bold="1" ss:Color="#FFFFFF"/>
   <Interior ss:Color="#00634B" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="2"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="2"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1"/>
   </Borders>
  </Style>
  <Style ss:ID="Title">
   <Alignment ss:Vertical="Center" ss:Horizontal="Center"/>
   <Font ss:FontName="Arial" ss:Size="16" ss:Bold="1" ss:Color="#00634B"/>
  </Style>
  <Style ss:ID="Subtitle">
   <Alignment ss:Vertical="Center" ss:Horizontal="Center"/>
   <Font ss:FontName="Arial" ss:Size="12" ss:Color="#666666"/>
  </Style>
  <Style ss:ID="Data">
   <Alignment ss:Vertical="Center" ss:Horizontal="Right"/>
   <Font ss:FontName="Arial" ss:Size="11"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#DDDDDD"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#DDDDDD"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#DDDDDD"/>
   </Borders>
  </Style>
  <Style ss:ID="DataAlt">
   <Alignment ss:Vertical="Center" ss:Horizontal="Right"/>
   <Font ss:FontName="Arial" ss:Size="11"/>
   <Interior ss:Color="#F5F5F5" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#DDDDDD"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#DDDDDD"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#DDDDDD"/>
   </Borders>
  </Style>
 </Styles>
 <Worksheet ss:Name="تقرير الجلسة">
  <Table ss:ExpandedColumnCount="7" ss:ExpandedRowCount="{{ row_count }}" x:FullColumns="1" x:FullRows="1">
   <Column ss:Width="50"/>
   <Column ss:Width="120"/>
   <Column ss:Width="200"/>
   <Column ss:Width="180"/>
   <Column ss:Width="120"/>
   <Column ss:Width="100"/>
   <Column ss:Width="100"/>
   
   <!-- العنوان -->
   <Row ss:Height="30">
    <Cell ss:MergeAcross="6" ss:StyleID="Title"><Data ss:Type="String">المؤسسة العامة للتدريب التقني والمهني</Data></Cell>
   </Row>
   <Row ss:Height="20">
    <Cell ss:MergeAcross="6" ss:StyleID="Subtitle"><Data ss:Type="String">Technical and Vocational Training Corporation - TVTC</Data></Cell>
   </Row>
   <Row ss:Height="25">
    <Cell ss:MergeAcross="6" ss:StyleID="Subtitle"><Data ss:Type="String">تقرير جلسة اختبار - {{ session.course_name }}</Data></Cell>
   </Row>
   <Row ss:Height="10"/>
   
   <!-- معلومات الجلسة -->
   <Row ss:Height="20">
    <Cell ss:MergeAcross="6" ss:StyleID="Data"><Data ss:Type="String">التخصص: {{ session.specialization }} | التاريخ: {{ session.session_date.strftime('%Y-%m-%d') }} | الوقت: {{ session.session_time.strftime('%H:%M') }} | المعمل: {{ session.location }} | عدد المسجلين: {{ session.current_count }} / {{ session.max_capacity }}</Data></Cell>
   </Row>
   <Row ss:Height="10"/>
   
   <!-- رأس الجدول -->
   <Row ss:Height="25">
    <Cell ss:StyleID="Header"><Data ss:Type="String">#</Data></Cell>
    <Cell ss:StyleID="Header"><Data ss:Type="String">الرقم التدريبي</Data></Cell>
    <Cell ss:StyleID="Header"><Data ss:Type="String">الاسم الكامل</Data></Cell>
    <Cell ss:StyleID="Header"><Data ss:Type="String">البريد الإلكتروني</Data></Cell>
    <Cell ss:StyleID="Header"><Data ss:Type="String">رقم الجوال</Data></Cell>
    <Cell ss:StyleID="Header"><Data ss:Type="String">ترتيب الجلسة</Data></Cell>
    <Cell ss:StyleID="Header"><Data ss:Type="String">الحالة</Data></Cell>
   </Row>
   
   <!-- البيانات -->
   {% for trainee in session.trainees %}
   <Row ss:Height="20">
    <Cell ss:StyleID="{{ 'Data' if loop.index % 2 == 1 else 'DataAlt' }}"><Data ss:Type="Number">{{ loop.index }}</Data></Cell>
    <Cell ss:StyleID="{{ 'Data' if loop.index % 2 == 1 else 'DataAlt' }}"><Data ss:Type="String">{{ trainee.trainee_id }}</Data></Cell>
    <Cell ss:StyleID="{{ 'Data' if loop.index % 2 == 1 else 'DataAlt' }}"><Data ss:Type="String">{{ trainee.full_name }}</Data></Cell>
    <Cell ss:StyleID="{{ 'Data' if loop.index % 2 == 1 else 'DataAlt' }}"><Data ss:Type="String">{{ trainee.email }}</Data></Cell>
    <Cell ss:StyleID="{{ 'Data' if loop.index % 2 == 1 else 'DataAlt' }}"><Data ss:Type="String">{{ trainee.phone }}</Data></Cell>
    <Cell ss:StyleID="{{ 'Data' if loop.index % 2 == 1 else 'DataAlt' }}"><Data ss:Type="String">{{ trainee.registration_order }}</Data></Cell>
    <Cell ss:StyleID="{{ 'Data' if loop.index % 2 == 1 else 'DataAlt' }}"><Data ss:Type="String">{{ trainee.attendance_status }}</Data></Cell>
   </Row>
   {% endfor %}
   
   <Row ss:Height="10"/>
   <Row ss:Height="20">
    <Cell ss:MergeAcross="6" ss:StyleID="Subtitle"><Data ss:Type="String">تاريخ التقرير: {{ report_date }}</Data></Cell>
   </Row>
  </Table>
 </Worksheet>
</Workbook>
"""

def generate_excel_xml(session):
    """توليد تقرير Excel XML لجلسة معينة"""
    row_count = 10 + len(session.trainees)  # حساب عدد الصفوف
    
    xml_content = render_template_string(
        EXCEL_TEMPLATE,
        session=session,
        report_date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        row_count=row_count
    )
    
    return xml_content