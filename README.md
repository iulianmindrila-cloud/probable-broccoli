A modern Python desktop application built with CustomTkinter to manage personal income and expenses.
Track transactions, manage categories, filter by period, and export your data to CSV — all in an intuitive, dark-themed interface.

🧩 Features


📊 Add, edit, and delete transactions (income or expenses)


🗂️ Manage custom categories for both income and expenses


🗓️ Filter data by day, week, month, year, or custom date range


💾 Export all transactions to CSV for external use


📈 See your balance updated in real time


🪶 Built with CustomTkinter, offering a modern and clean UI


💡 Works as both .py script and compiled .exe (PyInstaller)



⚙️ Requirements
Install dependencies using pip:
pip install customtkinter tkcalendar

(SQLite3 and tkinter are included by default in most Python distributions.)

🚀 How to Run
Run the app directly:
python personal_finance_custom_tkinter_full26.py

When first launched, the app will automatically create a local database file (finante.db) and some default categories.

🪟 Building the Executable (.exe)
You can build a standalone Windows executable using PyInstaller:
pyinstaller --onefile --icon=icon.ico personal_finance_custom_tkinter_full26.py

This will generate an .exe file inside the dist/ folder.
Make sure the icon file (icon.ico) is located in the same folder as the Python script when building.

📁 Project Structure
/project-folder/
│
├── personal_finance_custom_tkinter_full26.py
├── icon.ico
├── requirements.txt
└── README.md


🧠 How It Works


Data is stored locally in an SQLite3 database (finante.db).


The resource_path() function ensures resources (like icons) are found both in development and in the compiled .exe.


The GUI is built with CustomTkinter for a consistent dark theme and smooth design.


Transactions are displayed in a Treeview widget with filtering, sorting, and quick access to edit or delete.



📝 Example Screenshot (optional)
(You can later add a screenshot by uploading it to GitHub and linking it here.)
![App Screenshot](screenshot.png)


👤 Author
Developed by Iulian Mîndrilă
🇷🇴 https://iulianm.ro

Vrei să ți-l traduc și într-o variantă completă în română (pentru un fișier README.md bilingv)?
