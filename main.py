# main.py
import os
import json
import base64
import io
import flet as ft
import qrcode
from PIL import Image
from datetime import datetime
from database import DatabaseManager
from utils import ar, MONTHS, get_target_month
from pdf_generator import generate_qr_pdf

# هوية بصرية موحدة - أخضر زمردي ودرجات محايدة
PINK = "#0F766E"       # اللون الأساسي
PURPLE = "#115E59"     # اللون الثانوي
GREEN = "#16A34A"
RED = "#DC5252"
AMBER = "#D97706"
BLUE = "#2563A8"
BG = "#F3F7F6"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#172B2A"
TEXT_MUTED = "#718381"

def make_qr_data_url(data, size=280):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

def main(page: ft.Page):
    page.title = "أبلة ولاء | إدارة السنتر"
    page.bgcolor = BG
    page.padding = 0
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=PINK)
    
    db = DatabaseManager()
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def make_header(title, color=PINK, back=None, actions=None):
        ctrls = []
        if back:
            ctrls.append(ft.IconButton(
                ft.Icons.ARROW_FORWARD, icon_color="white",
                tooltip=ar("رجوع"), on_click=back
            ))
        ctrls.append(ft.Text(
            ar(title), size=19, weight=ft.FontWeight.BOLD,
            color="white", expand=True, max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ))
        if actions:
            ctrls.extend(actions)
        return ft.Container(
            content=ft.Row(ctrls, spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=color,
            padding=ft.Padding.symmetric(horizontal=14, vertical=13),
            shadow=ft.BoxShadow(
                blur_radius=12, spread_radius=0,
                color=ft.Colors.with_opacity(0.13, "#123B37"),
                offset=ft.Offset(0, 3),
            ),
        )

    def snack(msg, color=GREEN):
        s = ft.SnackBar(content=ft.Text(ar(msg), color="white"), bgcolor=color)
        page.overlay.append(s)
        s.open = True
        page.update()

    # LOGIN
    def show_login():
        page.views.clear()
        pw = ft.TextField(label=ar("كلمة المرور"), password=True, can_reveal_password=True, width=350, text_align=ft.TextAlign.CENTER, border_color=PINK)
        err = ft.Text("", color=RED, size=13)
        def do_login(e):
            if pw.value == "12345": show_home()
            else:
                err.value = ar("كلمة المرور غلط")
                page.update()
        pw.on_submit = do_login
        page.views.append(ft.View(route="/login", bgcolor=BG, padding=0, vertical_alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Container(content=ft.Column([
                ft.Container(
                    content=ft.Icon(ft.Icons.SCHOOL_ROUNDED, size=54, color="white"),
                    width=92, height=92, bgcolor=PINK, border_radius=28,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Container(height=8), ft.Text(ar("مدير درس أبلة ولاء"), size=27, weight=ft.FontWeight.BOLD, color=TEXT_DARK),
                ft.Text(ar("إدارة أسهل • متابعة أدق • نتائج أفضل"), size=13, color=TEXT_MUTED),
                ft.Container(height=16), pw, err, ft.Container(height=8),
                ft.Button(content=ft.Text(ar("دخول"), size=18, color="white"), bgcolor=PINK, width=350, height=55, on_click=do_login, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                ft.Container(height=8), ft.Text(ar("كلمة المرور: 12345"), size=11, color=TEXT_MUTED),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=7), padding=30, bgcolor=CARD_BG, border_radius=24, width=430, shadow=ft.BoxShadow(blur_radius=28, spread_radius=1, color=ft.Colors.with_opacity(0.12, "#123B37"), offset=ft.Offset(0, 8)))
        ]))
        page.update()

    # HOME
    def show_home():
        page.views.clear()
        tm, ty = get_target_month()
        st = db.get_all_students()
        paid = db.get_paid_student_ids(tm, ty)
        total, p = len(st), len(paid)
        u, pct = total - p, int(p / max(total, 1) * 100)

        def stat(icon, lbl, val, col):
            return ft.Container(
                content=ft.Column([
                    ft.Text(icon, size=23),
                    ft.Text(str(val), size=25, weight=ft.FontWeight.BOLD, color=col),
                    ft.Text(ar(lbl), size=11, color=TEXT_MUTED),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                padding=14, bgcolor=CARD_BG, border_radius=18, expand=True,
                shadow=ft.BoxShadow(
                    blur_radius=10, color=ft.Colors.with_opacity(0.045, "#123B37"),
                    offset=ft.Offset(0, 3),
                ),
            )
        def abtn(icon, lbl, col, cb):
            return ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Icon(icon, size=25, color=col),
                        width=48, height=48, bgcolor="#FFFFFF",
                        border_radius=16, alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text(ar(lbl), size=12, color="white", weight=ft.FontWeight.BOLD),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                bgcolor=col, padding=12, border_radius=18, expand=True,
                on_click=cb, ink=True,
                shadow=ft.BoxShadow(
                    blur_radius=9, color=ft.Colors.with_opacity(0.10, col),
                    offset=ft.Offset(0, 3),
                ),
            )

        def do_export(e):
            try:
                name = f"walaa_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                candidates = ["/storage/emulated/0/Download", os.path.expanduser("~/storage/downloads"), os.path.expanduser("~")]
                target_dir = next((p_ for p_ in candidates if os.path.exists(p_)), os.path.expanduser("~"))
                path = os.path.join(target_dir, name)
                ok, msg = db.export_db(path)
                snack(f"✅ تم التصدير\n{path}" if ok else f"❌ {msg}", GREEN if ok else RED)
            except Exception as ex: snack(f"❌ خطأ: {ex}", RED)

        def on_import_result(e: ft.FilePickerResultEvent):
            if not e.files: return
            path = e.files[0].path
            try:
                ok, msg, errors = db.import_db(path)
                snack(msg if ok else f"خطأ: {msg}", GREEN if ok else RED)
                if ok: show_home()
            except Exception as ex: snack(f"❌ {ex}", RED)
        file_picker.on_result = on_import_result

        import_btn = ft.Container(content=ft.Column([ft.Icon(ft.Icons.UPLOAD_FILE, size=24, color="white"), ft.Text(ar("استيراد .db"), size=13, color="white", weight=ft.FontWeight.BOLD)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4), bgcolor=BLUE, padding=14, border_radius=14, expand=True, action=ft.PickFiles(file_picker, allow_multiple=False, allowed_extensions=["db"]), ink=True)
        export_btn = ft.Container(content=ft.Column([ft.Icon(ft.Icons.DOWNLOAD, size=24, color="white"), ft.Text(ar("تصدير .db"), size=13, color="white", weight=ft.FontWeight.BOLD)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4), bgcolor=GREEN, padding=14, border_radius=14, expand=True, on_click=do_export, ink=True)

        page.views.append(ft.View(route="/home", bgcolor=BG, padding=0, controls=[
            make_header("مدير درس أبلة ولاء", PINK, actions=[ft.IconButton(ft.Icons.EXIT_TO_APP, icon_color="white", on_click=lambda e: show_login())]),
            ft.Container(content=ft.Column([
                ft.Text(ar("💾 قاعدة البيانات"), size=16, weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Container(height=4), ft.Row([import_btn, export_btn], spacing=10), ft.Container(height=16),
                ft.Container(content=ft.Column([ft.Text(ar("الشهر المطلوب دفعه الآن"), size=13, color=BLUE), ft.Text(ar(f"{MONTHS[tm-1]} {ty}"), size=22, weight=ft.FontWeight.BOLD, color=BLUE)], spacing=2), padding=14, bgcolor="#DBEAFE", border_radius=14), ft.Container(height=8),
                ft.Row([stat("👥", "الطلاب", total, PINK), stat("✅", "دفعوا", p, GREEN)], spacing=8), ft.Row([stat("❌", "لم يدفعوا", u, RED), stat("📊", "النسبة", f"{pct}%", PURPLE)], spacing=8), ft.Container(height=16),
                ft.Text(ar("⚡ إجراءات سريعة"), size=16, weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Container(height=4),
                ft.Row([abtn(ft.Icons.PEOPLE, "الطلاب", PURPLE, lambda e: show_students()), abtn(ft.Icons.ADD, "إضافة", PINK, lambda e: show_add_student()), abtn(ft.Icons.QR_CODE_SCANNER, "مسح QR", GREEN, lambda e: show_scanner())], spacing=8),
                ft.Row([abtn(ft.Icons.PRINT, "طباعة", AMBER, lambda e: show_printer()), abtn(ft.Icons.BAR_CHART, "تقارير", BLUE, lambda e: show_reports()), abtn(ft.Icons.ARROW_BACK, "خروج", TEXT_MUTED, lambda e: show_login())], spacing=8),
            ], spacing=7, scroll=ft.ScrollMode.AUTO, expand=True), padding=18, expand=True)
        ]))
        page.update()

    # STUDENTS - بحث مباشر وفلاتر
    def show_students():
        page.views.clear()
        tm, ty = get_target_month()
        all_students = db.get_all_students()
        paid_ids = db.get_paid_student_ids(tm, ty)
        grades = sorted({str(x.get("year", "")) for x in all_students if x.get("year")})

        search = ft.TextField(
            hint_text=ar("ابحث بالاسم أو كود الطالب أو رقم الهاتف..."),
            prefix_icon=ft.Icons.SEARCH,
            suffix_icon=ft.Icons.CLEAR,
            on_change=lambda e: refresh_list(),
            border_color=PURPLE,
            expand=True,
        )
        grade_filter = ft.Dropdown(
            label=ar("تصفية حسب الصف"),
            value="الكل",
            options=[ft.dropdown.Option("الكل")] + [ft.dropdown.Option(g) for g in grades],
            on_select=lambda e: refresh_list(),
            expand=True,
        )
        payment_filter = ft.Dropdown(
            label=ar("حالة الدفع"),
            value="الكل",
            options=[ft.dropdown.Option("الكل"), ft.dropdown.Option("دفعوا"), ft.dropdown.Option("لم يدفعوا")],
            on_select=lambda e: refresh_list(),
            expand=True,
        )
        result_count = ft.Text("", size=12, color=TEXT_MUTED)
        list_column = ft.Column(spacing=7, scroll=ft.ScrollMode.AUTO, expand=True)

        def student_card(student):
            is_paid = student["id"] in paid_ids
            return ft.Container(
                content=ft.Row([
                    ft.Container(width=5, height=54, bgcolor=GREEN if is_paid else RED, border_radius=4),
                    ft.Column([
                        ft.Text(ar(student["name"]), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK),
                        ft.Text(ar(f'{student["code"]}  •  {student["year"]}'), size=11, color=TEXT_MUTED),
                        ft.Text(ar(f'{int(student["fee"])} جنيه شهريًا  •  {student.get("phone") or "لا يوجد هاتف"}'), size=10, color=TEXT_MUTED),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text(ar("مدفوع" if is_paid else "مطلوب"), size=11, color=GREEN if is_paid else RED, weight=ft.FontWeight.BOLD),
                        ft.Button(ar("فتح"), bgcolor=PURPLE, on_click=lambda e, sid=student["id"]: show_student_detail(sid)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                ], spacing=8),
                bgcolor=CARD_BG, padding=12, border_radius=16,
                shadow=ft.BoxShadow(
                    blur_radius=8, color=ft.Colors.with_opacity(0.045, "#123B37"),
                    offset=ft.Offset(0, 2),
                ),
            )

        def refresh_list():
            query = (search.value or "").strip().casefold()
            selected_grade = grade_filter.value or "الكل"
            selected_payment = payment_filter.value or "الكل"
            filtered = []
            for student in all_students:
                searchable = " ".join(str(student.get(k) or "") for k in ("name", "code", "phone", "year")).casefold()
                if query and query not in searchable:
                    continue
                if selected_grade != "الكل" and str(student.get("year")) != selected_grade:
                    continue
                paid_now = student["id"] in paid_ids
                if selected_payment == "دفعوا" and not paid_now:
                    continue
                if selected_payment == "لم يدفعوا" and paid_now:
                    continue
                filtered.append(student)
            result_count.value = ar(f"النتائج: {len(filtered)} من أصل {len(all_students)} طالب")
            list_column.controls.clear()
            if not filtered:
                list_column.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PERSON_SEARCH, size=48, color=TEXT_MUTED),
                        ft.Text(ar("لا توجد نتائج مطابقة"), color=TEXT_MUTED, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30, bgcolor=CARD_BG, border_radius=12,
                ))
            else:
                for student in sorted(filtered, key=lambda x: (str(x.get("year", "")), str(x.get("name", "")))):
                    list_column.controls.append(student_card(student))
            page.update()

        page.views.append(ft.View(
            route="/students", bgcolor=BG, padding=0,
            controls=[
                make_header("إدارة الطلاب", PURPLE, back=lambda e: show_home(), actions=[
                    ft.IconButton(ft.Icons.PERSON_ADD, icon_color="white", tooltip=ar("إضافة طالب"), on_click=lambda e: show_add_student())
                ]),
                ft.Container(content=ft.Column([
                    ft.Row([search], spacing=8),
                    ft.Row([grade_filter, payment_filter], spacing=8),
                    ft.Row([
                        ft.Container(content=ft.Text(ar(f"إجمالي الطلاب: {len(all_students)}"), color=BLUE, weight=ft.FontWeight.BOLD), bgcolor="#DBEAFE", padding=9, border_radius=9),
                        ft.Container(content=ft.Text(ar(f"دفعوا: {len(paid_ids)}"), color=GREEN, weight=ft.FontWeight.BOLD), bgcolor="#D1FAE5", padding=9, border_radius=9),
                    ], wrap=True),
                    result_count,
                    list_column,
                    ft.Button(ar("＋ إضافة طالب جديد"), icon=ft.Icons.ADD, bgcolor=PINK, color="white", on_click=lambda e: show_add_student(), width=400),
                ], spacing=9, expand=True), padding=12, expand=True)
            ]
        ))
        refresh_list()

    # ADD
    def show_add_student():
        page.views.clear()
        name, year = ft.TextField(label=ar("اسم الطالب"), width=500), ft.TextField(label=ar("الصف"), width=500)
        fee, phone = ft.TextField(label=ar("الرسوم"), value="120", width=500, keyboard_type=ft.KeyboardType.NUMBER), ft.TextField(label=ar("التليفون"), width=500)
        err = ft.Text("", color=RED, size=13)
        def save(e):
            if not (name.value or "").strip() or not (year.value or "").strip():
                err.value = ar("❌ اكتب الاسم والصف")
                page.update()
                return
            try: f = float(fee.value or 0)
            except: f = 0
            db.add_student(name.value.strip(), year.value.strip(), f, (phone.value or "").strip())
            snack("✅ تم الحفظ")
            show_students()
        page.views.append(ft.View(route="/add", bgcolor=BG, padding=0, controls=[make_header("إضافة طالب", PINK, back=lambda e: show_home()), ft.Container(content=ft.Column([name, year, fee, phone, err, ft.Container(height=10), ft.Row([ft.Button(ar("حفظ"), bgcolor=GREEN, expand=True, height=50, on_click=save, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))), ft.Button(ar("إلغاء"), bgcolor=TEXT_MUTED, expand=True, height=50, on_click=lambda e: show_home())], spacing=10)], spacing=10), padding=20, bgcolor=CARD_BG, border_radius=16, width=550)]))
        page.update()

    # EDIT STUDENT
    def show_edit_student(sid):
        page.views.clear()
        student = db.get_student_by_id(sid)
        if not student:
            show_students()
            return
        name = ft.TextField(label=ar("اسم الطالب"), value=student.get("name", ""), expand=True)
        year = ft.TextField(label=ar("الصف الدراسي"), value=student.get("year", ""), expand=True)
        fee = ft.TextField(label=ar("المصروف الشهري"), value=str(student.get("fee", 0)), keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        phone = ft.TextField(label=ar("رقم الهاتف"), value=student.get("phone", ""), keyboard_type=ft.KeyboardType.PHONE, expand=True)
        error = ft.Text("", color=RED, size=12)
        def save_edit(e):
            if not (name.value or "").strip() or not (year.value or "").strip():
                error.value = ar("الاسم والصف مطلوبان")
                page.update()
                return
            try:
                amount = float((fee.value or "0").replace(",", "."))
                if amount < 0: raise ValueError()
            except Exception:
                error.value = ar("اكتب قيمة رسوم صحيحة")
                page.update()
                return
            db.update_student(sid, name.value.strip(), year.value.strip(), amount, (phone.value or "").strip())
            snack("تم تحديث بيانات الطالب")
            show_student_detail(sid)
        page.views.append(ft.View(route="/edit", bgcolor=BG, padding=0, controls=[
            make_header("تعديل بيانات الطالب", PURPLE, back=lambda e: show_student_detail(sid)),
            ft.Container(content=ft.Column([
                ft.Text(ar(f'كود الطالب: {student["code"]}'), color=TEXT_MUTED, size=12),
                name, year, fee, phone, error,
                ft.Button(ar("حفظ التعديلات"), icon=ft.Icons.SAVE, bgcolor=GREEN, color="white", on_click=save_edit, width=400, height=48),
                ft.Button(ar("رجوع بدون حفظ"), on_click=lambda e: show_student_detail(sid), width=400),
            ], spacing=12), padding=18, bgcolor=CARD_BG, border_radius=14, expand=True)
        ]))
        page.update()

    # DETAIL
    def show_student_detail(sid, selected_year=None):
        page.views.clear()
        s = db.get_student_by_id(sid)
        if not s:
            show_students()
            return

        tm, current_year = get_target_month()
        payment_year = int(selected_year) if selected_year is not None else current_year

        # السنوات السابقة القريبة + السنة الحالية + عشر سنوات قادمة،
        # مع إضافة أي سنوات موجودة بالفعل في سجل هذا الطالب.
        year_values = set(range(datetime.now().year - 5, datetime.now().year + 11))
        year_values.add(current_year)
        try:
            year_values.update(db.get_payment_years_for_student(sid))
        except Exception:
            pass
        year_options = sorted(year_values)

        payments = db.get_payments_for_student(sid, payment_year)
        paid_months = {p['month'] for p in payments}
        payload = json.dumps({"code": s['code'], "name": s['name'], "year": s['year'], "fee": s['fee']}, ensure_ascii=False)

        year_picker = ft.Dropdown(
            label=ar("سنة الدفع"),
            value=str(payment_year),
            options=[ft.dropdown.Option(str(y)) for y in year_options],
            on_select=lambda e: show_student_detail(sid, int(e.control.value)),
            width=220,
        )

        def toggle(m):
            def h(e):
                db.toggle_payment(sid, m, payment_year, s['fee'])
                show_student_detail(sid, payment_year)
            return h

        month_rows = []
        for start in range(1, 13, 4):
            row_items = []
            for m in range(start, min(start + 4, 13)):
                is_p = m in paid_months
                is_t = payment_year == current_year and m == tm
                col = GREEN if is_p else (AMBER if is_t else "#E2E8F0")
                status = "✓ دفع" if is_p else ("مطلوب" if is_t else "—")
                row_items.append(ft.Container(
                    content=ft.Text(ar(f"{MONTHS[m-1]}\n{status}"), size=11,
                                    color="white" if (is_p or is_t) else TEXT_DARK,
                                    text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD),
                    bgcolor=col, padding=8, border_radius=8, expand=True,
                    on_click=toggle(m), ink=True, height=60,
                    alignment=ft.Alignment(0, 0)
                ))
            month_rows.append(ft.Row(row_items, spacing=6))

        def show_qr(e):
            def close(e2):
                dlg.open = False
                page.update()
            dlg = ft.AlertDialog(
                title=ft.Text(ar("كود QR"), color=PINK),
                content=ft.Column([ft.Text(ar(s['name']), size=16, weight=ft.FontWeight.BOLD),
                                   ft.Image(src=make_qr_data_url(payload), width=280, height=280)],
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                actions=[ft.TextButton(ar("إغلاق"), on_click=close)]
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        page.views.append(ft.View(
            route="/detail", bgcolor=BG, padding=0,
            controls=[
                make_header(s['name'], PINK, back=lambda e: show_students(), actions=[
                    ft.IconButton(ft.Icons.EDIT, icon_color="white", tooltip=ar("تعديل البيانات"), on_click=lambda e: show_edit_student(sid)),
                    ft.IconButton(ft.Icons.QR_CODE, icon_color="white", tooltip=ar("عرض QR"), on_click=show_qr)
                ]),
                ft.Container(content=ft.Column([
                    ft.Container(content=ft.Column([
                        ft.Text(ar(f"الكود: {s['code']}"), size=12, color=TEXT_MUTED),
                        ft.Text(ar(f"الصف: {s['year']}"), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK),
                        ft.Text(ar(f"الرسوم: {int(s['fee'])} ج/شهر"), size=14, color=PINK)
                    ], spacing=4), padding=14, bgcolor=CARD_BG, border_radius=12),
                    ft.Container(height=8),
                    ft.Row([ft.Text(ar("💰 سجل المدفوعات"), size=15, weight=ft.FontWeight.BOLD, color=PINK, expand=True), year_picker],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(ar(f"اختر السنة لتسجيل أو مراجعة مدفوعاتها — {payment_year}"), size=11, color=TEXT_MUTED),
                    *month_rows
                ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True), padding=16, expand=True)
            ]
        ))
        page.update()

    # SCANNER
    def show_scanner():
        page.views.clear()
        page.views.append(ft.View(route="/scan", bgcolor=BG, padding=0, controls=[make_header("مسح QR", GREEN, back=lambda e: show_home()), ft.Container(content=ft.Column([ft.Icon(ft.Icons.PHOTO_CAMERA_OUTLINED, size=100, color=TEXT_MUTED), ft.Container(height=16), ft.Text(ar("📷 ميزة الكاميرا قيد التطوير"), size=18, weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Container(height=24), ft.Button(ar("رجوع"), bgcolor=GREEN, width=200, height=50, on_click=lambda e: show_home())], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, expand=True), padding=16, expand=True)]))
        page.update()

    # PRINTER - واجهة إنشاء PDF مطورة
    def show_printer():
        page.views.clear()
        years = db.get_all_years()
        grade_dd = ft.Dropdown(
            label=ar("اختر الصف"),
            options=[ft.dropdown.Option("كل الصفوف")] + [ft.dropdown.Option(y) for y in years],
            value="كل الصفوف", expand=True, border_color="#D8E5E2",
            focused_border_color=PINK, bgcolor="#FFFFFF",
        )
        status_dd = ft.Dropdown(
            label=ar("فلترة حالة الدفع"),
            options=[ft.dropdown.Option("الكل"), ft.dropdown.Option("المدفوعين فقط"), ft.dropdown.Option("غير المدفوعين فقط")],
            value="الكل", expand=True, border_color="#D8E5E2",
            focused_border_color=PINK, bgcolor="#FFFFFF",
        )
        cards = ft.TextField(
            label=ar("عدد الكروت في الصفحة"), value="9", width=170,
            keyboard_type=ft.KeyboardType.NUMBER, text_align=ft.TextAlign.CENTER,
            border_color="#D8E5E2", focused_border_color=PINK,
        )
        result = ft.Text("", size=12, color=TEXT_DARK, selectable=True)
        result_box = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, color=TEXT_MUTED), result],
                           vertical_alignment=ft.CrossAxisAlignment.START, spacing=10),
            bgcolor="#F1F5F4", padding=14, border_radius=14,
            border=ft.border.all(1, "#E1EAE7"), visible=False,
        )

        def update_preview(e=None):
            try:
                n = int(cards.value or 9)
                if n < 1 or n > 100:
                    preview.value = ar("اختر عددًا من 1 إلى 100 كارت")
                    preview.color = RED
                else:
                    preview.value = ar("كلما قل العدد كبر رمز QR وأصبح أوضح في الطباعة")
                    preview.color = TEXT_MUTED
            except Exception:
                preview.value = ar("اكتب عددًا صحيحًا من 1 إلى 100")
                preview.color = RED
            page.update()

        preview = ft.Text(ar("كلما قل العدد كبر رمز QR وأصبح أوضح في الطباعة"), size=11, color=TEXT_MUTED)
        cards.on_change = update_preview

        def section_label(number, title, subtitle):
            return ft.Row([
                ft.Container(content=ft.Text(str(number), color="white", weight=ft.FontWeight.BOLD, size=13),
                             width=28, height=28, alignment=ft.Alignment(0, 0),
                             bgcolor=PINK, border_radius=9),
                ft.Column([
                    ft.Text(ar(title), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK),
                    ft.Text(ar(subtitle), size=10, color=TEXT_MUTED),
                ], spacing=2, expand=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        def gen(e):
            students = db.get_all_students()
            if grade_dd.value != "كل الصفوف":
                students = [s for s in students if s['year'] == grade_dd.value]
            tm, ty = get_target_month()
            paid = db.get_paid_student_ids(tm, ty)
            if status_dd.value == "المدفوعين فقط":
                students = [s for s in students if s['id'] in paid]
            elif status_dd.value == "غير المدفوعين فقط":
                students = [s for s in students if s['id'] not in paid]
            if not students:
                result.value = ar("لا يوجد طلاب مطابقون للاختيارات الحالية")
                result.color = RED
                result_box.bgcolor = "#FEF2F2"
                result_box.visible = True
                page.update()
                return
            try:
                pp = int(cards.value or 9)
                if pp < 1 or pp > 100:
                    raise ValueError
            except Exception:
                result.value = ar("من فضلك أدخل عددًا صحيحًا من 1 إلى 100")
                result.color = RED
                result_box.bgcolor = "#FEF2F2"
                result_box.visible = True
                page.update()
                return
            generate_button.disabled = True
            generate_button.text = ar("جارٍ إنشاء الملف...")
            page.update()
            success, path = generate_qr_pdf(students, pp, paid_ids=paid)
            generate_button.disabled = False
            generate_button.text = ar("إنشاء ملف PDF الآن")
            if success:
                result.value = ar(f"تم إنشاء الملف بنجاح\nعدد الطلاب: {len(students)}\nعدد الكروت في الصفحة: {pp}\nمكان الحفظ: {path}")
                result.color = GREEN
                result_box.bgcolor = "#ECFDF5"
            else:
                result.value = ar(f"تعذر إنشاء الملف: {path}")
                result.color = RED
                result_box.bgcolor = "#FEF2F2"
            result_box.visible = True
            page.update()

        generate_button = ft.Button(
            content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF, color="white"),
                            ft.Text(ar("إنشاء ملف PDF الآن"), color="white", weight=ft.FontWeight.BOLD)],
                           alignment=ft.MainAxisAlignment.CENTER, spacing=9),
            bgcolor=PINK, color="white", height=54, expand=True, on_click=gen,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=14)),
        )

        intro = ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Icon(ft.Icons.PICTURE_AS_PDF, size=32, color="white"),
                             width=58, height=58, alignment=ft.Alignment(0, 0),
                             bgcolor=ft.Colors.with_opacity(0.18, "white"), border_radius=16),
                ft.Column([
                    ft.Text(ar("مركز إنشاء ملفات PDF"), size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text(ar("جهّز كروت الطلاب ورموز QR للطباعة بسهولة"), size=11, color="#E5F4F1"),
                ], spacing=5, expand=True),
            ], spacing=13, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=18, bgcolor=PINK, border_radius=20,
        )
        filter_card = ft.Container(
            content=ft.Column([
                section_label("1", "تحديد الطلاب", "اختَر الصف وحالة الدفع المطلوبة"),
                grade_dd, status_dd,
            ], spacing=13),
            bgcolor=CARD_BG, padding=16, border_radius=18,
            border=ft.border.all(1, "#E4ECE9"),
        )
        layout_card = ft.Container(
            content=ft.Column([
                section_label("2", "تنسيق صفحة الطباعة", "حدد عدد الكروت التي تظهر في كل صفحة"),
                ft.Row([
                    ft.Column([cards, preview], spacing=5, expand=True),
                    ft.Container(content=ft.Column([
                        ft.Icon(ft.Icons.GRID_VIEW, color=PINK, size=25),
                        ft.Text(ar("شبكة الكروت"), size=10, color=TEXT_MUTED, weight=ft.FontWeight.BOLD),
                        ft.Text("A4", size=18, color=TEXT_DARK, weight=ft.FontWeight.BOLD),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                        padding=10, bgcolor="#F0F7F5", border_radius=13, width=100),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Container(content=ft.Text(ar("4–6 كروت: QR كبير"), size=10, color=GREEN), bgcolor="#EAF8F0", padding=8, border_radius=9, expand=True),
                    ft.Container(content=ft.Text(ar("9–16: متوسط"), size=10, color=BLUE), bgcolor="#EEF5FC", padding=8, border_radius=9, expand=True),
                    ft.Container(content=ft.Text(ar("20–30: صغير"), size=10, color=AMBER), bgcolor="#FFF7E8", padding=8, border_radius=9, expand=True),
                ], spacing=6),
            ], spacing=13),
            bgcolor=CARD_BG, padding=16, border_radius=18,
            border=ft.border.all(1, "#E4ECE9"),
        )
        page.views.append(ft.View(
            route="/printer", bgcolor=BG, padding=0,
            controls=[
                make_header("إنشاء وطباعة PDF", PINK, back=lambda e: show_home()),
                ft.Container(content=ft.Column([
                    intro, filter_card, layout_card, generate_button, result_box,
                    ft.Row([ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, size=16, color=AMBER),
                            ft.Text(ar("سيتم حفظ الملف تلقائيًا في مجلد التنزيلات إذا كان متاحًا."), size=10, color=TEXT_MUTED)], spacing=7),
                ], spacing=14, scroll=ft.ScrollMode.AUTO, expand=True), padding=16, expand=True),
            ],
        ))
        page.update()

    # REPORTS
    def show_reports():
        page.views.clear()
        tm, ty = get_target_month()
        students = db.get_all_students()
        paid = db.get_paid_student_ids(tm, ty)
        by_grade = {}
        for s in students: by_grade.setdefault(s['year'], []).append(s)
        sections = [ft.Container(content=ft.Row([ft.Text(ar(g), size=14, weight=ft.FontWeight.BOLD, color=PURPLE, expand=True), ft.Text(f"✅ {len([s for s in arr if s['id'] in paid])}  ❌ {len([s for s in arr if s['id'] not in paid])}", size=13, color=TEXT_DARK)]), bgcolor=CARD_BG, padding=12, border_radius=10) for g, arr in sorted(by_grade.items())]
        page.views.append(ft.View(route="/reports", bgcolor=BG, padding=0, controls=[make_header(f"تقرير {MONTHS[tm-1]} {ty}", BLUE, back=lambda e: show_home()), ft.Container(content=ft.Column([ft.Row([ft.Container(content=ft.Column([ft.Text(str(len(students)), size=24, weight=ft.FontWeight.BOLD, color=PINK), ft.Text(ar("الطلاب"), size=11, color=TEXT_MUTED)]), bgcolor=CARD_BG, padding=12, border_radius=10, expand=True), ft.Container(content=ft.Column([ft.Text(str(len(paid)), size=24, weight=ft.FontWeight.BOLD, color=GREEN), ft.Text(ar("دفعوا"), size=11, color=TEXT_MUTED)]), bgcolor=CARD_BG, padding=12, border_radius=10, expand=True), ft.Container(content=ft.Column([ft.Text(str(len(students)-len(paid)), size=24, weight=ft.FontWeight.BOLD, color=RED), ft.Text(ar("لم يدفعوا"), size=11, color=TEXT_MUTED)]), bgcolor=CARD_BG, padding=12, border_radius=10, expand=True)], spacing=8), ft.Container(height=16), ft.Text(ar("📊 التفصيل حسب الصف"), size=15, weight=ft.FontWeight.BOLD, color=TEXT_DARK), *sections], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True), padding=16, expand=True)]))
        page.update()

    show_login()

if __name__ == "__main__":
    ft.run(main)
