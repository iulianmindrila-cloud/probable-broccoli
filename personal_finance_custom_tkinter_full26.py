import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime, date, timedelta
import os # PENTRU ICONIȚĂ
import sys # PENTRU ICONIȚĂ

DB_FILE = "finante.db"

# NOU: Funcție esențială pentru a găsi fișierele (ca icon.ico)
# atât în modul de dezvoltare (script .py) cât și în .exe (PyInstaller)
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creează un folder temporar și stochează calea în _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Nu rulează într-un pachet PyInstaller
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# -------------------- DATABASE --------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS tranzactii (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, tip TEXT, categorie TEXT, suma REAL, descriere TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS categorii (id INTEGER PRIMARY KEY AUTOINCREMENT, nume TEXT UNIQUE, tip TEXT)")
    conn.commit()
    defaults = [
        ('Salariu', 'Venit'), ('Investiții', 'Venit'), ('Cadouri', 'Venit'),
        ('Mâncare', 'Cheltuială'), ('Transport', 'Cheltuială'),
        ('Facturi', 'Cheltuială'), ('Divertisment', 'Cheltuială'),
        ('Sănătate', 'Cheltuială'), ('Altele', 'Cheltuială')
    ]
    for n, t in defaults:
        try:
            c.execute('INSERT OR IGNORE INTO categorii (nume, tip) VALUES (?,?)', (n, t))
        except:
            pass
    conn.commit()
    conn.close()

def get_categories(tip=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if tip:
        c.execute('SELECT nume FROM categorii WHERE tip=? ORDER BY nume', (tip,))
    else:
        c.execute('SELECT nume FROM categorii ORDER BY tip,nume')
    r = [x[0] for x in c.fetchall()]
    conn.close()
    return r

def add_category(name, tip):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO categorii (nume,tip) VALUES (?,?)', (name, tip))
    conn.commit()
    conn.close()

def delete_category(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE tranzactii SET categorie=? WHERE categorie=?', ('Altele', name))
    c.execute('DELETE FROM categorii WHERE nume=?', (name,))
    conn.commit()
    conn.close()

# -------------------- HELPERS FOR DATES --------------------
def start_of_week(d):
    # assuming week starts on Monday
    return d - timedelta(days=d.weekday())

def end_of_week(d):
    return start_of_week(d) + timedelta(days=6)

# -------------------- APP --------------------
class FinanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("💰 Evidență Financiară Personală")
        
        # --- Adăugare iconiță ---
        try:
            # Folosim resource_path pentru a găsi icon.ico
            self.iconbitmap(resource_path('icon.ico'))
        except Exception as e:
            print(f"Atenție: Nu s-a putut încărca 'icon.ico'. Motiv: {e}")
        # --- Sfârșit modificare ---

        self.geometry("1180x680")
        
        # --- AICI A FOST EROAREA ---
        # Am înlocuit ct_k.StringVar cu ctk.StringVar
        self.selected_filter = ctk.StringVar(value="Toate") 
        # --- SFÂRȘIT CORECȚIE ---
        
        self.custom_from = None
        self.custom_to = None
        self.category_filter_var = ctk.StringVar(value="Toate")

        self.create_sidebar()
        self.create_main_area()
        self.refresh_categories()
        self.update_filter_categories() 
        self.refresh_data()

        self.edit_frame = None
        self.category_manager_frame = None
        self.category_manager_visible = False

    # -------------------- SIDEBAR --------------------
    def create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=320, corner_radius=8)
        sidebar.pack(side="left", fill="y", padx=12, pady=8)

        ctk.CTkLabel(sidebar, text="Meniu", font=("Arial", 20, "bold")).pack(pady=(10, 8))

        # --- FILTRU PERIOADĂ ---
        ctk.CTkLabel(sidebar, text="Filtru perioadă:").pack(anchor="w", padx=10)
        self.period_var = ctk.StringVar(value="Toate")
        period_values = ["Toate", "Azi", "Săptămâna curentă", "Luna curentă", "Anul curent", "Custom"]
        self.period_menu = ctk.CTkOptionMenu(sidebar, variable=self.period_var, values=period_values, command=self.on_period_change)
        self.period_menu.pack(padx=10, pady=(0,8), fill="x")

        # custom date range (hidden unless Custom selected)
        self.custom_frame = ctk.CTkFrame(sidebar)
        # will be packed when needed
        ctk.CTkLabel(self.custom_frame, text="De la:").grid(row=0, column=0, sticky='w', padx=(0,6))
        self.custom_from_entry = DateEntry(self.custom_frame, date_pattern='yyyy-mm-dd')
        self.custom_from_entry.grid(row=0, column=1, padx=(0,6))
        ctk.CTkLabel(self.custom_frame, text="Până la:").grid(row=1, column=0, sticky='w', padx=(0,6))
        self.custom_to_entry = DateEntry(self.custom_frame, date_pattern='yyyy-mm-dd')
        self.custom_to_entry.grid(row=1, column=1, padx=(0,6))
        ctk.CTkButton(self.custom_frame, text="Aplică filtru", command=self.apply_custom_filter).grid(row=2, column=0, columnspan=2, pady=(6,0))

        # --- FILTRU CATEGORIE ---
        ctk.CTkLabel(sidebar, text="Filtru categorie:").pack(anchor="w", padx=10, pady=(8,0))
        self.category_filter_menu = ctk.CTkOptionMenu(sidebar, variable=self.category_filter_var, values=["Toate"], command=self.on_category_filter_change)
        self.category_filter_menu.pack(padx=10, pady=(0,8), fill="x")

        # --- DATE TRANZACȚIE ---
        ctk.CTkLabel(sidebar, text="Data tranzacției:").pack(anchor="w", padx=10, pady=(8,0))
        self.date_entry = DateEntry(sidebar, date_pattern="yyyy-mm-dd")
        self.date_entry.set_date(datetime.now())
        self.date_entry.pack(padx=10, pady=(0, 8), fill="x")

        ctk.CTkLabel(sidebar, text="Tip:").pack(anchor="w", padx=10)
        self.entry_tip = ctk.StringVar(value="Venit")
        tip_menu = ctk.CTkOptionMenu(sidebar, variable=self.entry_tip, values=["Venit", "Cheltuială"], command=self.on_tip_change)
        tip_menu.pack(padx=10, pady=(0, 8), fill="x")

        ctk.CTkLabel(sidebar, text="Categorie:").pack(anchor="w", padx=10)
        self.entry_categorie = ctk.CTkEntry(sidebar, placeholder_text="Categorie nouă sau existentă")
        self.entry_categorie.pack(padx=10, pady=(0, 6), fill="x")
        self.cat_selected = ctk.StringVar(value="")
        self.cat_menu = ctk.CTkOptionMenu(sidebar, variable=self.cat_selected, values=[""], command=self.on_cat_select)
        self.cat_menu.pack(padx=10, pady=(0, 8), fill="x")

        ctk.CTkLabel(sidebar, text="Sumă (RON):").pack(anchor="w", padx=10)
        self.entry_suma = ctk.CTkEntry(sidebar, placeholder_text="Sumă")
        self.entry_suma.pack(padx=10, pady=(0, 8), fill="x")

        ctk.CTkLabel(sidebar, text="Descriere:").pack(anchor="w", padx=10)
        self.entry_descriere = ctk.CTkEntry(sidebar, placeholder_text="Descriere (opțional)")
        self.entry_descriere.pack(padx=10, pady=(0, 12), fill="x")

        ctk.CTkButton(sidebar, text="Adaugă tranzacție", command=self.add_transaction).pack(padx=10, pady=(0, 8), fill="x")
        ctk.CTkButton(sidebar, text="Export CSV", command=self.export_csv).pack(padx=10, pady=(0, 8), fill="x")
        
        self.cat_manager_button = ctk.CTkButton(sidebar, text="Gestionarea categoriilor", command=self.toggle_category_manager)
        self.cat_manager_button.pack(padx=10, pady=(0, 8), fill="x")
        
        ctk.CTkButton(sidebar, text="Ieșire", fg_color="red", command=self.quit).pack(side="bottom", padx=10, pady=12, fill="x")

    def on_cat_select(self, value):
        self.entry_categorie.delete(0, 'end')
        self.entry_categorie.insert(0, value)

    def on_tip_change(self, value):
        cats = get_categories(value)
        self.cat_menu.configure(values=cats)
        if cats:
            self.cat_menu.set(cats[0])

    def on_period_change(self, value):
        if value == "Custom":
            self.custom_frame.pack(padx=10, pady=(6,8), fill="x")
        else:
            try:
                self.custom_frame.forget()
            except:
                pass
            self.refresh_data()

    def on_category_filter_change(self, value):
        self.refresh_data()

    def apply_custom_filter(self):
        try:
            d1 = self.custom_from_entry.get_date()
            d2 = self.custom_to_entry.get_date()
            if d1 > d2:
                messagebox.showwarning("Atenție", "Data 'De la' nu poate fi după 'Până la'.")
                return
            self.custom_from = d1
            self.custom_to = d2
            self.refresh_data()
        except Exception as e:
            messagebox.showerror("Eroare", f"Date invalide: {e}")

    # -------------------- MAIN --------------------
    def create_main_area(self):
        self.main_area = ctk.CTkFrame(self)
        self.main_area.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=8)

        ctk.CTkLabel(self.main_area, text="Tranzacții", font=("Arial", 20, "bold")).pack(pady=(8, 10))

        cols = ("id", "data", "tip", "categorie", "suma", "descriere")
        self.tree = ttk.Treeview(self.main_area, columns=cols, show="headings", selectmode="extended")
        for col, text, w in [
            ("id", "ID", 40), ("data", "Data", 100), ("tip", "Tip", 80),
            ("categorie", "Categorie", 140), ("suma", "Sumă (RON)", 100), ("descriere", "Descriere", 260)
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor="center" if col in ["id", "data", "tip"] else "w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(6, 4))

        bottom = ctk.CTkFrame(self.main_area)
        bottom.pack(fill="x", padx=12, pady=(4, 12))
        self.label_balanta = ctk.CTkLabel(bottom, text="Balanță: 0 RON", font=("Arial", 16, "bold"))
        self.label_balanta.pack(side="left", padx=(6, 12))

        ctk.CTkButton(bottom, text="Editează tranzacție", command=self.show_edit_section).pack(side="left", padx=6)
        ctk.CTkButton(bottom, text="Șterge selectate", fg_color="#e53935", command=self.delete_selected).pack(side="left", padx=6)

    # -------------------- REFRESH --------------------
    def refresh_categories(self):
        cats = get_categories(self.entry_tip.get())
        self.cat_menu.configure(values=cats)
        if cats:
            self.cat_menu.set(cats[0])

    def update_filter_categories(self):
        cats = get_categories() 
        filter_values = ["Toate"] + sorted(cats)
        current_val = self.category_filter_var.get()
        
        self.category_filter_menu.configure(values=filter_values)
        
        if current_val not in filter_values:
            self.category_filter_var.set("Toate")

    def _rows_in_date_range(self, rows):
        per = self.period_var.get()
        today = date.today()
        filtered = []
        for r in rows:
            try:
                r_date = datetime.strptime(r[1], "%Y-%m-%d").date()
            except:
                continue
            if per == "Toate":
                include = True
            elif per == "Azi":
                include = (r_date == today)
            elif per == "Săptămâna curentă":
                include = (start_of_week(today) <= r_date <= end_of_week(today))
            elif per == "Luna curentă":
                include = (r_date.year == today.year and r_date.month == today.month)
            elif per == "Anul curent":
                include = (r_date.year == today.year)
            elif per == "Custom" and self.custom_from and self.custom_to:
                include = (self.custom_from <= r_date <= self.custom_to)
            else:
                include = True
            if include:
                filtered.append(r)
        return filtered

    def refresh_data(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id,data,tip,categorie,suma,descriere FROM tranzactii ORDER BY date(data) DESC")
        rows = c.fetchall()
        conn.close()

        rows = self._rows_in_date_range(rows)

        selected_cat = self.category_filter_var.get()
        if selected_cat != "Toate":
            rows = [r for r in rows if r[3] == selected_cat]

        for i in self.tree.get_children():
            self.tree.delete(i)
        
        total_v = total_c = 0
        for r in rows:
            tid, dt, tip, cat, suma, desc = r
            self.tree.insert("", "end", values=(tid, dt, tip, cat, f"{suma:.2f}", desc))
            if tip == "Venit":
                total_v += suma
            else:
                total_c += suma

        bal = total_v - total_c
        color = "#00FF7F" if bal >= 0 else "#FF4C4C"
        sign = "+" if bal >= 0 else ""
        self.label_balanta.configure(text=f"Balanță: {sign}{bal:.2f} RON", text_color=color)

    # -------------------- ADD / DELETE --------------------
    def add_transaction(self):
        data = self.date_entry.get_date().strftime("%Y-%m-%d")
        tip = self.entry_tip.get()
        categorie = self.entry_categorie.get().strip()
        suma = self.entry_suma.get().strip()
        descriere = self.entry_descriere.get().strip()

        if not (suma and categorie):
            messagebox.showwarning("Eroare", "Completează suma și categoria.")
            return
        try:
            suma = float(suma)
        except:
            messagebox.showwarning("Eroare", "Suma trebuie numerică.")
            return

        add_category(categorie, tip)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO tranzactii (data,tip,categorie,suma,descriere) VALUES (?,?,?,?,?)", (data, tip, categorie, suma, descriere))
        conn.commit()
        conn.close()
        self.entry_suma.delete(0, 'end')
        self.entry_categorie.delete(0, 'end')
        self.entry_descriere.delete(0, 'end')
        self.refresh_categories()
        
        self.update_filter_categories() 
        self.refresh_data()

    def delete_selected(self):
        sels = self.tree.selection()
        if not sels:
            messagebox.showwarning("Atenție", "Selectează una sau mai multe tranzacții pentru ștergere.")
            return
        if not messagebox.askyesno("Confirmare", f"Sigur ștergi {len(sels)} tranzacții selectate?"):
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        for s in sels:
            tid = self.tree.item(s)["values"][0]
            c.execute("DELETE FROM tranzactii WHERE id=?", (tid,))
        conn.commit()
        conn.close()
        self.refresh_data()
        messagebox.showinfo("Succes", f"{len(sels)} tranzacții au fost șterse.")

    # -------------------- EDIT SECTION --------------------
    def show_edit_section(self):
        if self.category_manager_visible:
            self.toggle_category_manager()
            
        if self.edit_frame:
            self.edit_frame.destroy()
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenție", "Selectează o tranzacție pentru editare.")
            return
        vals = self.tree.item(sel[0])["values"]
        tid, dt, tip, cat, suma, desc = vals

        self.edit_frame = ctk.CTkFrame(self.main_area)
        self.edit_frame.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(self.edit_frame, text="✏️ Editare tranzacție", font=("Arial", 15, "bold")).pack(anchor="w", padx=12, pady=(4, 4))

        fields = ctk.CTkFrame(self.edit_frame)
        fields.pack(fill="x", padx=12)
        ctk.CTkLabel(fields, text="Data:").grid(row=0, column=0, sticky="w")
        self.edit_date = DateEntry(fields, date_pattern="yyyy-mm-dd")
        self.edit_date.set_date(dt)
        self.edit_date.grid(row=0, column=1, padx=6, pady=4)

        ctk.CTkLabel(fields, text="Categorie:").grid(row=1, column=0, sticky="w")
        cats = sorted(get_categories())
        self.edit_cat = ctk.CTkOptionMenu(fields, values=cats)
        self.edit_cat.set(cat)
        self.edit_cat.grid(row=1, column=1, padx=6, pady=4)

        ctk.CTkLabel(fields, text="Sumă (RON):").grid(row=2, column=0, sticky="w")
        self.edit_sum = ctk.CTkEntry(fields)
        self.edit_sum.insert(0, suma)
        self.edit_sum.grid(row=2, column=1, padx=6, pady=4)

        ctk.CTkLabel(fields, text="Descriere:").grid(row=3, column=0, sticky="w")
        self.edit_desc = ctk.CTkEntry(fields)
        self.edit_desc.insert(0, desc)
        self.edit_desc.grid(row=3, column=1, padx=6, pady=4)

        ctk.CTkButton(self.edit_frame, text="Salvează modificările", command=lambda: self.save_edit(tid)).pack(padx=12, pady=8)
        ctk.CTkButton(self.edit_frame, text="Anulează", fg_color="#9e9e9e", command=lambda: self.edit_frame.destroy()).pack(padx=12, pady=(0,8))

    def save_edit(self, tid):
        new_date = self.edit_date.get_date().strftime("%Y-%m-%d")
        new_cat = self.edit_cat.get()
        new_sum = self.edit_sum.get()
        new_desc = self.edit_desc.get()
        try:
            new_sum = float(new_sum)
        except:
            messagebox.showerror("Eroare", "Sumă invalidă.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE tranzactii SET data=?, categorie=?, suma=?, descriere=? WHERE id=?", (new_date, new_cat, new_sum, new_desc, tid))
        conn.commit()
        conn.close()
        messagebox.showinfo("Succes", "Tranzacția a fost actualizată.")
        self.refresh_data()
        self.edit_frame.destroy()


    # -------------------- CATEGORY MANAGER --------------------
    
    def toggle_category_manager(self):
        if self.category_manager_visible:
            if self.category_manager_frame:
                self.category_manager_frame.destroy()
            self.category_manager_frame = None
            self.cat_manager_button.configure(text="Gestionarea categoriilor")
            self.category_manager_visible = False
        else:
            if self.edit_frame:
                self.edit_frame.destroy()
                self.edit_frame = None
            
            self.create_category_manager_ui()
            self.cat_manager_button.configure(text="Închide secțiunea categorii")
            self.category_manager_visible = True

    def create_category_manager_ui(self):
        self.category_manager_frame = ctk.CTkFrame(self.main_area, corner_radius=8)
        self.category_manager_frame.pack(side="bottom", fill="x", expand=False, padx=12, pady=(6, 12))

        ctk.CTkLabel(self.category_manager_frame, text="📂 Gestionare categorii", font=("Arial", 16, "bold")).pack(anchor="w", pady=(6,6), padx=12)

        cols = ctk.CTkFrame(self.category_manager_frame)
        cols.pack(fill="x", expand=True, padx=12, pady=(0, 12))
        left = ctk.CTkFrame(cols)
        right = ctk.CTkFrame(cols)
        left.pack(side="left", fill="both", expand=True, padx=(0,6))
        right.pack(side="left", fill="both", expand=True, padx=(6,0))

        # Left - Venit
        ctk.CTkLabel(left, text="Venituri", font=("Arial", 13, "bold")).pack(anchor="w", pady=(0,6))
        self.list_venit = ttk.Treeview(left, columns=("n",), show="headings", height=6) 
        self.list_venit.heading("n", text="Categorie")
        self.list_venit.pack(fill="both", expand=True, padx=6, pady=(0,6))
        ven_frame = ctk.CTkFrame(left)
        ven_frame.pack(fill="x", padx=6)
        self.ven_new_entry = ctk.CTkEntry(ven_frame, placeholder_text="Nume categorie")
        self.ven_new_entry.pack(side="left", fill="x", expand=True, padx=(0,6))
        ctk.CTkButton(ven_frame, text="Adaugă", command=lambda: self._add_cat_from_manager("Venit", "ven")).pack(side="left")
        ctk.CTkButton(ven_frame, text="Șterge", fg_color="#e53935", command=lambda: self._delete_cat_from_manager("ven")).pack(side="left", padx=(6,0))

        # Right - Cheltuială
        ctk.CTkLabel(right, text="Cheltuieli", font=("Arial", 13, "bold")).pack(anchor="w", pady=(0,6))
        self.list_chelt = ttk.Treeview(right, columns=("n",), show="headings", height=6) 
        self.list_chelt.heading("n", text="Categorie")
        self.list_chelt.pack(fill="both", expand=True, padx=6, pady=(0,6))
        che_frame = ctk.CTkFrame(right)
        che_frame.pack(fill="x", padx=6)
        self.che_new_entry = ctk.CTkEntry(che_frame, placeholder_text="Nume categorie")
        self.che_new_entry.pack(side="left", fill="x", expand=True, padx=(0,6))
        ctk.CTkButton(che_frame, text="Adaugă", command=lambda: self._add_cat_from_manager("Cheltuială", "che")).pack(side="left")
        ctk.CTkButton(che_frame, text="Șterge", fg_color="#e53935", command=lambda: self._delete_cat_from_manager("che")).pack(side="left", padx=(6,0))

        self._populate_category_lists()

    def _populate_category_lists(self):
        for i in self.list_venit.get_children():
            self.list_venit.delete(i)
        for i in self.list_chelt.get_children():
            self.list_chelt.delete(i)
        ven = get_categories("Venit")
        che = get_categories("Cheltuială")
        for v in ven:
            self.list_venit.insert("", "end", values=(v,))
        for c in che:
            self.list_chelt.insert("", "end", values=(c,))
        
        self.refresh_categories()
        self.update_filter_categories() 
        self.refresh_data() 

    def _add_cat_from_manager(self, tip, side):
        name = (self.ven_new_entry.get().strip() if side=="ven" else self.che_new_entry.get().strip())
        if not name:
            messagebox.showwarning("Atenție", "Introdu numele categoriei.")
            return
        add_category(name, tip)
        self._populate_category_lists()
        if side=="ven":
            self.ven_new_entry.delete(0, 'end')
        else:
            self.che_new_entry.delete(0, 'end')

    def _delete_cat_from_manager(self, side):
        tree = self.list_venit if side=="ven" else self.list_chelt
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Atenție", "Selectează o categorie pentru ștergere.")
            return
        name = tree.item(sel[0])['values'][0]
        if name in ['Altele']:
             messagebox.showwarning("Atenție", "Categoria 'Altele' nu poate fi ștearsă.")
             return
        if not messagebox.askyesno("Confirmare", f"Ștergi categoria '{name}'? (Toate tranzacțiile vor fi mutate în 'Altele')"):
            return
        delete_category(name)
        self._populate_category_lists()

    # -------------------- EXPORT --------------------
    def export_csv(self):
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not fpath:
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT data,tip,categorie,suma,descriere FROM tranzactii ORDER BY date(data) DESC")
        rows = c.fetchall()
        conn.close()
        with open(fpath, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Data", "Tip", "Categorie", "Sumă", "Descriere"])
            w.writerows(rows)
        messagebox.showinfo("Export complet", f"Datele au fost exportate în {fpath}")

# -------------------- RUN --------------------
if __name__ == "__main__":
    init_db()
    app = FinanceApp()
    app.mainloop()