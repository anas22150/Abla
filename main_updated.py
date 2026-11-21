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

# ألوان
PINK = "#EC4899"
PURPLE = "#8B5CF6"
GREEN = "#10B981"
RED = "#EF4444"
AMBER = "#F59E0B"
BLUE = "#1E3A8A"
BG = "#FDF2F8"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#64748B"

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
    page.title = "مدير درس أبلة ولاء"
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
        if back: ctrls.append(ft.IconButton(ft.Icons.ARROW_FORWARD, icon_color="white", on_click=back))
        ctrls.append(ft.Text(ar(title), size=20, weight=ft.FontWeight.BOLD, color="white", expand=True))
        if actions: ctrls.extend(actions)
        return ft.Container(content=ft.Row(ctrls), bgcolor=color, padding=ft.Padding.symmetric(horizontal=16, vertical=12))

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
                ft.Icon(ft.Icons.SCHOOL, size=100, color=PINK),
                ft.Container(height=8), ft.Text(ar("مدير درس أبلة ولاء"), size=30, weight=ft.FontWeight.BOLD, color=PINK),
                ft.Text(ar("سجّل دخولك للمتابعة"), size=14, color=TEXT_MUTED),
                ft.Container(height=16), pw, err, ft.Container(height=8),
                ft.Button(content=ft.Text(ar("دخول"), size=18, color="white"), bgcolor=PINK, width=350, height=55, on_click=do_login, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                ft.Container(height=8), ft.Text(ar("كلمة المرور: 12345"), size=11, color=TEXT_MUTED),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6), padding=40, bgcolor=CARD_BG, border_radius=24, width=430, shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.15, PINK)))
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
            return ft.Container(content=ft.Column([ft.Text(icon, size=24), ft.Text(str(val), size=24, weight=ft.FontWeight.BOLD, color=col), ft.Text(ar(lbl), size=11, color=TEXT_MUTED)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2), padding=12, bgcolor=CARD_BG, border_radius=14, expand=True)
        def abtn(icon, lbl, col, cb):
            return ft.Container(content=ft.Column([ft.Icon(icon, size=28, color="white"), ft.Text(ar(lbl), size=13, color="white", weight=ft.FontWeight.BOLD)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6), bgcolor=col, padding=16, border_radius=14, expand=True, on_click=cb, ink=True)

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
                ft.Text(ar("💾 قاعدة البيانات"), size=16, weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Container(height=4), ft.Row([import_btn, export_btn], spacing=8), ft.Container(height=16),
                ft.Container(content=ft.Column([ft.Text(ar("الشهر المطلوب دفعه الآن"), size=13, color=BLUE), ft.Text(ar(f"{MONTHS[tm-1]} {ty}"), size=22, weight=ft.FontWeight.BOLD, color=BLUE)], spacing=2), padding=14, bgcolor="#DBEAFE", border_radius=14), ft.Container(height=8),
                ft.Row([stat("👥", "الطلاب", total, PINK), stat("✅", "دفعوا", p, GREEN)], spacing=8), ft.Row([stat("❌", "لم يدفعوا", u, RED), stat("📊", "النسبة", f"{pct}%", PURPLE)], spacing=8), ft.Container(height=16),
                ft.Text(ar("⚡ إجراءات سريعة"), size=16, weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Container(height=4),
                ft.Row([abtn(ft.Icons.PEOPLE, "الطلاب", PURPLE, lambda e: show_students()), abtn(ft.Icons.ADD, "إضافة", PINK, lambda e: show_add_student()), abtn(ft.Icons.QR_CODE_SCANNER, "مسح QR", GREEN, lambda e: show_scanner())], spacing=8),
                ft.Row([abtn(ft.Icons.PRINT, "طباعة", AMBER, lambda e: show_printer()), abtn(ft.Icons.BAR_CHART, "تقارير", BLUE, lambda e: show_reports()), abtn(ft.Icons.ARROW_BACK, "خروج", TEXT_MUTED, lambda e: show_login())], spacing=8),
            ], spacing=4, scroll=ft.ScrollMode.AUTO, expand=True), padding=16, expand=True)
        ]))
        page.update()

    # STUDENTS - تقسيم حسب الصف ثم حالة الدفع
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
        list_column = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

        def student_card(student, is_paid):
            return ft.Container(
                content=ft.Row([
                    ft.Container(width=5, height=58, bgcolor=GREEN if is_paid else RED, border_radius=4),
                    ft.Column([
                        ft.Text(ar(student["name"]), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK),
                        ft.Text(ar(f'{student["code"]}  •  {student["year"]}'), size=11, color=TEXT_MUTED),
                        ft.Text(ar(f'{int(student["fee"])} جنيه شهريًا  •  {student.get("phone") or "لا يوجد هاتف"}'), size=10, color=TEXT_MUTED),
                    ], spacing=2, expand=True),
                    ft.Column([
                        ft.Text(ar("✓ دفع" if is_paid else "لم يدفع"), size=11, color=GREEN if is_paid else RED, weight=ft.FontWeight.BOLD),
                        ft.Button(ar("فتح"), bgcolor=PURPLE, on_click=lambda e, sid=student["id"]: show_student_detail(sid)),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                ], spacing=8),
                bgcolor=CARD_BG, padding=10, border_radius=12,
            )

        def group_title(label, count, color, icon):
            return ft.Container(
                content=ft.Row([
                    ft.Icon(icon, color=color, size=18),
                    ft.Text(ar(label), color=color, weight=ft.FontWeight.BOLD, size=13, expand=True),
                    ft.Container(content=ft.Text(str(count), color="white", weight=ft.FontWeight.BOLD, size=12), bgcolor=color, padding=ft.Padding.symmetric(horizontal=10, vertical=4), border_radius=20),
                ]),
                padding=ft.Padding.only(top=5, bottom=3),
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
                is_paid = student["id"] in paid_ids
                if selected_payment == "دفعوا" and not is_paid:
                    continue
                if selected_payment == "لم يدفعوا" and is_paid:
                    continue
                filtered.append(student)

            result_count.value = ar(f"النتائج: {len(filtered)} من أصل {len(all_students)} طالب")
            list_column.controls.clear()
            grouped = {}
            for student in filtered:
                grouped.setdefault(str(student.get("year") or "بدون صف"), []).append(student)

            if not grouped:
                list_column.controls.append(ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.PERSON_SEARCH, size=48, color=TEXT_MUTED),
                        ft.Text(ar("لا توجد نتائج مطابقة"), color=TEXT_MUTED, size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30, bgcolor=CARD_BG, border_radius=12,
                ))
            else:
                for grade in sorted(grouped):
                    grade_students = sorted(grouped[grade], key=lambda x: str(x.get("name", "")))
                    paid_students = [x for x in grade_students if x["id"] in paid_ids]
                    unpaid_students = [x for x in grade_students if x["id"] not in paid_ids]
                    section_controls = [
                        ft.Row([
                            ft.Icon(ft.Icons.SCHOOL, color=PURPLE, size=20),
                            ft.Text(ar(grade), size=16, weight=ft.FontWeight.BOLD, color=PURPLE, expand=True),
                            ft.Text(ar(f"{len(grade_students)} طالب"), size=12, color=TEXT_MUTED),
                        ]),
                        ft.Divider(color="#E9D5FF", height=8),
                        group_title("الطلاب الذين دفعوا", len(paid_students), GREEN, ft.Icons.CHECK_CIRCLE),
                    ]
                    if paid_students:
                        section_controls.extend([student_card(x, True) for x in paid_students])
                    else:
                        section_controls.append(ft.Text(ar("لا يوجد طلاب دفعوا في هذا الصف"), size=11, color=TEXT_MUTED))
                    section_controls.append(group_title("الطلاب الذين لم يدفعوا", len(unpaid_students), RED, ft.Icons.SCHEDULE))
                    if unpaid_students:
                        section_controls.extend([student_card(x, False) for x in unpaid_students])
                    else:
                        section_controls.append(ft.Text(ar("كل طلاب الصف دفعوا ✓"), size=11, color=GREEN))
                    list_column.controls.append(ft.Container(
                        content=ft.Column(section_controls, spacing=7),
                        bgcolor="#FFFFFF", padding=12, border_radius=16,
                    ))
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
    def show_student_detail(sid):
        page.views.clear()
        s = db.get_student_by_id(sid)
        if not s: show_students(); return
        tm, ty = get_target_month()
        payments = db.get_payments_for_student(sid, ty)
        paid_months = {p['month'] for p in payments}
        payload = json.dumps({"code": s['code'], "name": s['name'], "year": s['year'], "fee": s['fee']}, ensure_ascii=False)
        def toggle(m):
            def h(e):
                db.toggle_payment(sid, m, ty, s['fee'])
                show_student_detail(sid)
            return h
        month_rows = []
        for start in range(1, 13, 4):
            row_items = []
            for m in range(start, min(start+4, 13)):
                is_p, is_t = m in paid_months, (m == tm)
                col = GREEN if is_p else (AMBER if is_t else "#E2E8F0")
                status = "✓ دفع" if is_p else ("مطلوب" if is_t else "—")
                row_items.append(ft.Container(content=ft.Text(ar(f"{MONTHS[m-1]}\n{status}"), size=11, color="white" if (is_p or is_t) else TEXT_DARK, text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD), bgcolor=col, padding=8, border_radius=8, expand=True, on_click=toggle(m), ink=True, height=60, alignment=ft.Alignment(0, 0)))
            month_rows.append(ft.Row(row_items, spacing=6))
        def show_qr(e):
            def close(e2): dlg.open = False; page.update()
            dlg = ft.AlertDialog(title=ft.Text(ar("كود QR"), color=PINK), content=ft.Column([ft.Text(ar(s['name']), size=16, weight=ft.FontWeight.BOLD), ft.Image(src=make_qr_data_url(payload), width=280, height=280)], horizontal_alignment=ft.CrossAxisAlignment.CENTER), actions=[ft.TextButton(ar("إغلاق"), on_click=close)])
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
        page.views.append(ft.View(route="/detail", bgcolor=BG, padding=0, controls=[make_header(s['name'], PINK, back=lambda e: show_students(), actions=[ft.IconButton(ft.Icons.EDIT, icon_color="white", tooltip=ar("تعديل البيانات"), on_click=lambda e: show_edit_student(sid)), ft.IconButton(ft.Icons.QR_CODE, icon_color="white", tooltip=ar("عرض QR"), on_click=show_qr)]), ft.Container(content=ft.Column([ft.Container(content=ft.Column([ft.Text(ar(f"الكود: {s['code']}"), size=12, color=TEXT_MUTED), ft.Text(ar(f"الصف: {s['year']}"), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Text(ar(f"الرسوم: {int(s['fee'])} ج/شهر"), size=14, color=PINK)], spacing=4), padding=14, bgcolor=CARD_BG, border_radius=12), ft.Container(height=8), ft.Text(ar(f"💰 مدفوعات {ty}"), size=15, weight=ft.FontWeight.BOLD, color=PINK), *month_rows], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True), padding=16, expand=True)]))
        page.update()

    # SCANNER
    def show_scanner():
        page.views.clear()
        page.views.append(ft.View(route="/scan", bgcolor=BG, padding=0, controls=[make_header("مسح QR", GREEN, back=lambda e: show_home()), ft.Container(content=ft.Column([ft.Icon(ft.Icons.PHOTO_CAMERA_OUTLINED, size=100, color=TEXT_MUTED), ft.Container(height=16), ft.Text(ar("📷 ميزة الكاميرا قيد التطوير"), size=18, weight=ft.FontWeight.BOLD, color=TEXT_DARK), ft.Container(height=24), ft.Button(ar("رجوع"), bgcolor=GREEN, width=200, height=50, on_click=lambda e: show_home())], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, expand=True), padding=16, expand=True)]))
        page.update()

    # PRINTER
    def show_printer():
        page.views.clear()
        years = db.get_all_years()
        grade_dd = ft.Dropdown(label=ar("الصف"), options=[ft.dropdown.Option("كل الصفوف")] + [ft.dropdown.Option(y) for y in years], value="كل الصفوف", width=350)
        status_dd = ft.Dropdown(label=ar("حالة الدفع"), options=[ft.dropdown.Option("الكل"), ft.dropdown.Option("المدفوعين فقط"), ft.dropdown.Option("غير المدفوعين فقط")], value="الكل", width=350)
        cards = ft.TextField(label=ar("عدد الكروت/صفحة"), value="9", width=200, keyboard_type=ft.KeyboardType.NUMBER)
        result = ft.Text("", size=12, color=TEXT_DARK)
        def gen(e):
            students = db.get_all_students()
            if grade_dd.value != "كل الصفوف": students = [s for s in students if s['year'] == grade_dd.value]
            tm, ty = get_target_month()
            paid = db.get_paid_student_ids(tm, ty)
            if status_dd.value == "المدفوعين فقط": students = [s for s in students if s['id'] in paid]
            elif status_dd.value == "غير المدفوعين فقط": students = [s for s in students if s['id'] not in paid]
            if not students: result.value = ar("❌ لا يوجد طلاب"); result.color = RED; page.update(); return
            try: pp = max(1, min(int(cards.value or 9), 100))
            except: pp = 9
            success, path = generate_qr_pdf(students, pp, paid_ids=paid)
            result.value = ar(f"✅ تم ({len(students)} طالب، {pp} كارت/صفحة)\n{path}") if success else ar(f"❌ فشل: {path}")
            result.color = GREEN if success else RED
            page.update()
        page.views.append(ft.View(route="/printer", bgcolor=BG, padding=0, controls=[make_header("طباعة PDF", AMBER, back=lambda e: show_home()), ft.Container(content=ft.Column([ft.Text(ar("1️⃣ الصف"), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK), grade_dd, ft.Text(ar("2️⃣ حالة الدفع"), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK), status_dd, ft.Text(ar("3️⃣ عدد الكروت/صفحة"), size=14, weight=ft.FontWeight.BOLD, color=TEXT_DARK), cards, ft.Text(ar("💡 4-6 كروت = QR أكبر | 30 كارت = QR أصغر"), size=11, color=TEXT_MUTED), ft.Container(height=10), ft.Button(ar("📄 توليد PDF"), bgcolor=AMBER, width=300, height=55, on_click=gen), ft.Container(height=10), result], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True), padding=20, expand=True)]))
        page.update()

    # REPORTS - لوحة تقارير برسوم توضيحية
    def show_reports():
        page.views.clear()
        tm, ty = get_target_month()
        students = db.get_all_students()
        paid_ids = db.get_paid_student_ids(tm, ty)
        total = len(students)
        paid_students = [s for s in students if s["id"] in paid_ids]
        unpaid_students = [s for s in students if s["id"] not in paid_ids]
        paid_count = len(paid_students)
        unpaid_count = len(unpaid_students)
        ratio = paid_count / total if total else 0
        by_grade = {}
        for student in students:
            by_grade.setdefault(str(student.get("year") or "بدون صف"), []).append(student)

        def metric_card(icon, label, value, color, tint):
            return ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(icon, color=color, size=20), ft.Text(ar(label), size=11, color=TEXT_MUTED, expand=True)]),
                    ft.Text(str(value), size=27, weight=ft.FontWeight.BOLD, color=color),
                ], spacing=5),
                bgcolor=tint, padding=13, border_radius=14, expand=True,
            )

        grade_cards = []
        for grade, grade_students in sorted(by_grade.items()):
            grade_paid = sum(1 for s in grade_students if s["id"] in paid_ids)
            grade_unpaid = len(grade_students) - grade_paid
            grade_ratio = grade_paid / len(grade_students) if grade_students else 0
            grade_cards.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(content=ft.Icon(ft.Icons.SCHOOL, color=PURPLE, size=20), bgcolor="#F3E8FF", padding=9, border_radius=10),
                        ft.Column([
                            ft.Text(ar(grade), size=15, weight=ft.FontWeight.BOLD, color=TEXT_DARK),
                            ft.Text(ar(f"{len(grade_students)} طالب إجمالي"), size=11, color=TEXT_MUTED),
                        ], spacing=2, expand=True),
                        ft.Text(ar(f"{round(grade_ratio*100)}%"), size=19, weight=ft.FontWeight.BOLD, color=GREEN if grade_ratio >= .5 else AMBER),
                    ]),
                    ft.ProgressBar(value=grade_ratio, color=GREEN, bgcolor="#FEE2E2", height=12),
                    ft.Row([
                        ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=GREEN, size=16), ft.Text(ar(f"دفعوا: {grade_paid}"), color=GREEN, size=12, weight=ft.FontWeight.BOLD)], spacing=4),
                        ft.Row([ft.Icon(ft.Icons.CANCEL, color=RED, size=16), ft.Text(ar(f"لم يدفعوا: {grade_unpaid}"), color=RED, size=12, weight=ft.FontWeight.BOLD)], spacing=4),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ], spacing=10),
                bgcolor=CARD_BG, padding=14, border_radius=15,
            ))

        page.views.append(ft.View(
            route="/reports", bgcolor=BG, padding=0,
            controls=[
                make_header(f"تقارير {MONTHS[tm-1]} {ty}", BLUE, back=lambda e: show_home()),
                ft.Container(content=ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(ar("ملخص التحصيل الشهري"), size=16, weight=ft.FontWeight.BOLD, color="white"),
                            ft.Text(ar(f"{round(ratio*100)}% من الطلاب سددوا الاشتراك"), size=12, color="#E0E7FF"),
                            ft.ProgressBar(value=ratio, color="#34D399", bgcolor="#64748B", height=14),
                            ft.Row([
                                ft.Text(ar(f"✓ {paid_count} دفعوا"), color="white", size=12, weight=ft.FontWeight.BOLD),
                                ft.Text(ar(f"{unpaid_count} لم يدفعوا"), color="white", size=12, weight=ft.FontWeight.BOLD),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ], spacing=10),
                        bgcolor=BLUE, padding=17, border_radius=18,
                    ),
                    ft.Row([
                        metric_card(ft.Icons.GROUP, "إجمالي الطلاب", total, PURPLE, "#F3E8FF"),
                        metric_card(ft.Icons.CHECK_CIRCLE, "دفعوا", paid_count, GREEN, "#D1FAE5"),
                        metric_card(ft.Icons.SCHEDULE, "لم يدفعوا", unpaid_count, RED, "#FEE2E2"),
                    ], spacing=8),
                    ft.Row([
                        ft.Text(ar("تفصيل كل صف"), size=17, weight=ft.FontWeight.BOLD, color=TEXT_DARK, expand=True),
                        ft.Container(content=ft.Text(ar(f"{len(by_grade)} صفوف"), color=PURPLE, size=11, weight=ft.FontWeight.BOLD), bgcolor="#F3E8FF", padding=8, border_radius=20),
                    ]),
                    *(grade_cards if grade_cards else [ft.Text(ar("لا يوجد طلاب مسجلون حتى الآن"), color=TEXT_MUTED)]),
                ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True), padding=14, expand=True)
            ]
        ))
        page.update()
    show_login()

if __name__ == "__main__":
    ft.run(main)
