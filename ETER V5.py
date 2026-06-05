import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
import requests
from io import BytesIO
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


# GHI bulanan dalam kWh/m²/bulan 

MONTHLY_GHI_KWH = {
    "Jan": 4.6, "Feb": 4.6, "Mar": 4.9, "Apr": 5.1, "Mei": 5.3, "Jun": 5.4,
    "Jul": 5.7, "Ags": 6.3, "Sep": 6.7, "Okt": 6.3, "Nov": 5.1, "Des": 4.8
}
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Ags", "Sep", "Okt", "Nov", "Des"]

# Komponen sistem
PANEL_OPTIONS = {
    "Monocrystalline 550 Wp": {"power": 550, "area": 1, "efficiency": 0.20, "price_per_wp": 11000},
    "Polycrystalline 450 Wp": {"power": 450, "area": 1, "efficiency": 0.18, "price_per_wp": 9500},
}
INVERTER_OPTIONS = {
    "SMA Sunny Tripower 10000TL": {"power_kw": 10, "price_per_kw": 5600000},
    "Growatt 8000TL3-S": {"power_kw": 8, "price_per_kw": 3200000},
}

class AstrophagePV:
    def __init__(self, root):
        self.root = root
        self.root.title("Astrophage PV - Digitalisasi Analisis Presisi PLTS Atap")
        self.root.geometry("1400x800")

        # Variabel
        self.lat = tk.DoubleVar(value=-6.8912)
        self.lon = tk.DoubleVar(value=107.6106)
        self.tilt = tk.IntVar(value=15)
        self.azimuth = tk.IntVar(value=180)
        self.panel_type = tk.StringVar(value="Monocrystalline 550 Wp")
        self.inverter_type = tk.StringVar(value="SMA Sunny Tripower 10000TL")
        self.shading_loss = tk.DoubleVar(value=5.0)  # persen
        self.roof_area = tk.DoubleVar(value=0.0)

        self.map_img = None
        self.polygon_points = []
        self.polygon_id = None
        self.drawing = False

        self.setup_ui()
        self.update_azimuth_info()

    def setup_ui(self):
        left = ttk.LabelFrame(self.root, text="Parameter & Kontrol", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Lokasi
        ttk.Label(left, text="Lokasi (Studi Kasus: ITB Ganesha)", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, pady=5, sticky='w')
        ttk.Label(left, text="Latitude:").grid(row=1, column=0, sticky='w')
        ttk.Entry(left, textvariable=self.lat, width=12).grid(row=1, column=1)
        ttk.Label(left, text="Longitude:").grid(row=2, column=0, sticky='w')
        ttk.Entry(left, textvariable=self.lon, width=12).grid(row=2, column=1)
        self.coord_label = ttk.Label(left, text="")
        self.coord_label.grid(row=3, column=0, columnspan=2)
        self.update_coord_label()
        ttk.Button(left, text="Ambil Peta", command=self.fetch_map).grid(row=4, column=0, columnspan=2, pady=10)

        # Area PLTS
        ttk.Label(left, text="Area PLTS (Gambar Poligon)", font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=2, pady=(10,0), sticky='w')
        self.draw_btn = ttk.Button(left, text="Mulai Gambar", command=self.toggle_draw, state=tk.DISABLED)
        self.draw_btn.grid(row=6, column=0, columnspan=2, pady=5)
        self.reset_btn = ttk.Button(left, text="Reset Area", command=self.reset_polygon, state=tk.DISABLED)
        self.reset_btn.grid(row=7, column=0, columnspan=2, pady=5)
        ttk.Label(left, text="Luas atap terdeteksi:").grid(row=8, column=0, sticky='w')
        self.area_label = ttk.Label(left, text="0.0 m²", relief="sunken", width=12)
        self.area_label.grid(row=8, column=1)
        ttk.Label(left, text="Faktor kelayakan:").grid(row=9, column=0, sticky='w')
        self.faktor_label = ttk.Label(left, text="0.78", relief="sunken", width=12)
        self.faktor_label.grid(row=9, column=1)
        ttk.Label(left, text="Luas atap efektif:").grid(row=10, column=0, sticky='w')
        self.effective_label = ttk.Label(left, text="0.0 m²", relief="sunken", width=12)
        self.effective_label.grid(row=10, column=1)

        # Orientasi
        ttk.Label(left, text="Orientasi Sistem", font=('Arial', 10, 'bold')).grid(row=11, column=0, columnspan=2, pady=(10,0), sticky='w')
        ttk.Label(left, text="Kemiringan (tilt):").grid(row=12, column=0, sticky='w')
        tilt_scale = ttk.Scale(left, from_=0, to=60, variable=self.tilt, orient=tk.HORIZONTAL, length=100)
        tilt_scale.grid(row=12, column=1)
        ttk.Label(left, textvariable=self.tilt).grid(row=12, column=2)
        ttk.Label(left, text="Arah hadap (azimuth):").grid(row=13, column=0, sticky='w')
        az_scale = ttk.Scale(left, from_=0, to=360, variable=self.azimuth, orient=tk.HORIZONTAL, length=100)
        az_scale.grid(row=13, column=1)
        ttk.Label(left, textvariable=self.azimuth).grid(row=13, column=2)
        self.az_info = ttk.Label(left, text="", foreground="gray")
        self.az_info.grid(row=14, column=0, columnspan=3)

        # Komponen
        ttk.Label(left, text="Komponen Sistem", font=('Arial', 10, 'bold')).grid(row=15, column=0, columnspan=2, pady=(10,0), sticky='w')
        ttk.Label(left, text="Modul PV:").grid(row=16, column=0, sticky='w')
        panel_menu = ttk.Combobox(left, textvariable=self.panel_type, values=list(PANEL_OPTIONS.keys()), state="readonly")
        panel_menu.grid(row=16, column=1)
        ttk.Label(left, text="Inverter:").grid(row=17, column=0, sticky='w')
        inv_menu = ttk.Combobox(left, textvariable=self.inverter_type, values=list(INVERTER_OPTIONS.keys()), state="readonly")
        inv_menu.grid(row=17, column=1)
        ttk.Label(left, text="Shading loss (%):").grid(row=18, column=0, sticky='w')
        ttk.Scale(left, from_=0, to=30, variable=self.shading_loss, orient=tk.HORIZONTAL, length=100).grid(row=18, column=1)
        ttk.Label(left, textvariable=self.shading_loss).grid(row=18, column=2)

        ttk.Button(left, text="Hitung Potensi & Laporan", command=self.calculate).grid(row=19, column=0, columnspan=3, pady=20)

        self.status = ttk.Label(left, text="Siap", relief="sunken")
        self.status.grid(row=20, column=0, columnspan=3, sticky='we', pady=5)

        right = ttk.Frame(self.root)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.map_label = ttk.Label(right, text="Peta akan muncul di sini", background="white")
        self.map_label.pack(fill=tk.BOTH, expand=True)
        self.canvas = None

    def update_coord_label(self, event=None):
        lat = self.lat.get()
        lon = self.lon.get()
        lat_dir = "LS" if lat < 0 else "LU"
        lon_dir = "BT" if lon > 0 else "BB"
        self.coord_label.config(text=f"{abs(lat):.4f}° {lat_dir}, {abs(lon):.4f}° {lon_dir}")

    def update_azimuth_info(self):
        az = self.azimuth.get()
        if az == 0: d = "Utara"
        elif az == 90: d = "Timur"
        elif az == 180: d = "Selatan"
        elif az == 270: d = "Barat"
        else: d = f"{az}°"
        self.az_info.config(text=f"Panel menghadap {d}")

    def fetch_map(self):
        try:
            self.status.config(text="Mengunduh peta...")
            self.root.update()
            lat, lon = self.lat.get(), self.lon.get()
            zoom = 19
            n = 2**zoom
            x = (lon + 180) / 360 * n
            y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
            url = f"https://tile.openstreetmap.org/{zoom}/{int(x)}/{int(y)}.png"
            resp = requests.get(url, headers={"User-Agent": "Astrophage-PV/1.0"}, timeout=10)
            img = Image.open(BytesIO(resp.content))
            img = img.resize((800, 600), Image.Resampling.LANCZOS)
            self.map_img = ImageTk.PhotoImage(img)
            if self.canvas is None:
                self.canvas = tk.Canvas(self.map_label, width=800, height=600)
                self.canvas.pack(fill=tk.BOTH, expand=True)
            else:
                self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.map_img)
            self.canvas.bind("<Button-1>", self.on_click)
            self.status.config(text="Peta siap. Klik 'Mulai Gambar' untuk menentukan area PLTS.")
            self.draw_btn.config(state=tk.NORMAL)
            self.reset_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal ambil peta: {e}")
            self.status.config(text="Gagal ambil peta")

    def toggle_draw(self):
        self.drawing = not self.drawing
        if self.drawing:
            self.draw_btn.config(text="Sedang menggambar... (klik selesai)")
            self.status.config(text="Klik pada peta untuk menambah titik poligon. Minimal 3 titik.")
            self.polygon_points = []
            if self.polygon_id:
                self.canvas.delete(self.polygon_id)
                self.polygon_id = None
        else:
            self.draw_btn.config(text="Mulai Gambar")
            self.status.config(text="Mode gambar nonaktif")
            if len(self.polygon_points) >= 3:
                self.calc_area()
            else:
                messagebox.showwarning("Area tidak valid", "Gambar poligon dengan minimal 3 titik.")

    def on_click(self, event):
        if not self.drawing:
            return
        x, y = event.x, event.y
        self.polygon_points.append((x, y))
        r = 3
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="red", tags="point")
        if len(self.polygon_points) >= 2:
            px, py = self.polygon_points[-2]
            self.canvas.create_line(px, py, x, y, fill="red", width=2, tags="line")
        self.status.config(text=f"Titik ke-{len(self.polygon_points)}")

    def reset_polygon(self):
        self.polygon_points = []
        if self.polygon_id:
            self.canvas.delete(self.polygon_id)
            self.polygon_id = None
        self.canvas.delete("point")
        self.canvas.delete("line")
        self.roof_area.set(0)
        self.area_label.config(text="0.0 m²")
        self.effective_label.config(text="0.0 m²")
        self.status.config(text="Area direset")

    def calc_area(self):
        area_pixel = self.polygon_area(self.polygon_points)
        self.polygon_id = self.canvas.create_polygon(self.polygon_points, outline="green", fill="green", stipple="gray50")
        meter_per_pixel = 0.1
        area_m2 = area_pixel * (meter_per_pixel**2)
        self.roof_area.set(area_m2)
        self.area_label.config(text=f"{area_m2:.1f} m²")
        faktor = 0.78
        area_eff = area_m2 * faktor
        self.effective_label.config(text=f"{area_eff:.1f} m²")
        self.status.config(text=f"Luas atap terdeteksi: {area_m2:.1f} m², efektif: {area_eff:.1f} m²")
        self.drawing = False
        self.draw_btn.config(text="Mulai Gambar")

    def polygon_area(self, points):
        area = 0
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i+1)%n]
            area += x1*y2 - x2*y1
        return abs(area)/2

    def calculate(self):
        if self.roof_area.get() <= 0:
            messagebox.showwarning("Area belum ditentukan", "Gambar area PLTS pada peta terlebih dahulu.")
            return

        self.status.config(text="Menghitung potensi PLTS...")
        self.root.update()

        area_detected = self.roof_area.get()
        area_eff = area_detected * 0.55
        tilt = self.tilt.get()
        azimuth = self.azimuth.get()
        shading = self.shading_loss.get() / 100.0
        panel = PANEL_OPTIONS[self.panel_type.get()]
        inverter = INVERTER_OPTIONS[self.inverter_type.get()]

        # Faktor orientasi sederhana
        tilt_rad = math.radians(tilt)
        az_factor = 1.0 - min(0.3, abs(azimuth - 180) / 180.0)
        tilt_factor = math.cos(tilt_rad) * 0.9 + 0.1
        orientation_factor = tilt_factor * az_factor
        pr = 0.55

        monthly_energy = []
        total_energy = 0
        for month in MONTH_NAMES:
            ghi_month = MONTHLY_GHI_KWH[month]  # kWh/m² per bulan
            energy_month = area_eff * ghi_month * panel['efficiency'] * (1 - shading) * orientation_factor * pr *5
            monthly_energy.append(energy_month)
            total_energy += energy_month

        # Kapasitas
        panel_area = panel['area']
        max_panels = int(area_eff / panel_area)
        if max_panels <= 0:
            max_panels = 1
        dc_kwp = max_panels * panel['power'] / 1000
        inverter_kw = inverter['power_kw']
        if dc_kwp > inverter_kw:
            max_panels = int(inverter_kw * 1000 / panel['power'])
            dc_kwp = max_panels * panel['power'] / 1000
            area_eff_used = max_panels * panel_area
        else:
            area_eff_used = area_eff

        # Finansial
        capex_panel = max_panels * panel['power'] * panel['price_per_wp']
        capex_inverter = inverter['power_kw'] * inverter['price_per_kw']
        capex_install = dc_kwp * 1500000
        total_capex = capex_panel + capex_inverter + capex_install

        tariff = 1500
        annual_saving = total_energy * tariff
        o_m = total_capex * 0.01
        net_saving = annual_saving - o_m
        if net_saving > 0:
            payback = total_capex / net_saving
        else:
            payback = float('inf')

        losses = {
            "Shading": self.shading_loss.get(),
            "Orientation (tilt+azimuth)": (1 - orientation_factor) * 100,
            "Performance Ratio (other losses)": (1 - pr) * 100
        }

        self.result = {
            'area_detected': area_detected,
            'area_effective': area_eff,
            'area_used': area_eff_used,
            'panels': max_panels,
            'dc_kwp': dc_kwp,
            'annual_kwh': total_energy,
            'monthly_kwh': monthly_energy,
            'capex': total_capex,
            'annual_saving': annual_saving,
            'o_m': o_m,
            'net_saving': net_saving,
            'payback': payback,
            'losses': losses,
            'panel_name': self.panel_type.get(),
            'inverter_name': self.inverter_type.get(),
            'tilt': tilt,
            'azimuth': azimuth,
            'lat': self.lat.get(),
            'lon': self.lon.get(),
            'performance_ratio': pr * 100,
            'orientation_factor': orientation_factor
        }

        self.status.config(text="Perhitungan selesai. Buka laporan...")
        self.show_report()

    def show_report(self):
        win = tk.Toplevel(self.root)
        win.title("Laporan Potensi PLTS Atap - Astrophage PV")
        win.geometry("1100x800")

        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tab1 = ttk.Frame(notebook); notebook.add(tab1, text="Ringkasan")
        self.add_summary_tab(tab1)
        tab2 = ttk.Frame(notebook); notebook.add(tab2, text="Finansial")
        self.add_financial_tab(tab2)
        tab3 = ttk.Frame(notebook); notebook.add(tab3, text="Loss Diagram")
        self.add_loss_diagram(tab3)
        tab4 = ttk.Frame(notebook); notebook.add(tab4, text="Produksi Bulanan")
        self.add_monthly_chart(tab4)
        tab5 = ttk.Frame(notebook); notebook.add(tab5, text="Parameter")
        self.add_params_tab(tab5)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export TXT", command=self.export_txt).pack(side=tk.LEFT, padx=5)

    def add_summary_tab(self, parent):
        text = tk.Text(parent, wrap=tk.WORD, font=('Consolas', 10))
        text.pack(fill=tk.BOTH, expand=True)
        r = self.result
        summary = f"""
╔══════════════════════════════════════════════════════════════════╗
║              ASTROPHAGE PV - SIMULATION REPORT                   ║
╚══════════════════════════════════════════════════════════════════╝

Tanggal : {datetime.now().strftime('%d/%m/%Y %H:%M')}
Lokasi  : {r['lat']:.4f}, {r['lon']:.4f}

Luas atap terdeteksi   : {r['area_detected']:.1f} m²
Luas atap efektif      : {r['area_effective']:.1f} m²
Jumlah modul PV        : {r['panels']} unit
Kapasitas DC           : {r['dc_kwp']:.2f} kWp
Produksi energi tahunan: {r['annual_kwh']:.0f} kWh
Performance Ratio      : {r['performance_ratio']:.0f}%

Rekomendasi: {'LAYAK (payback < 10 tahun)' if r['payback'] < 10 else 'Perlu optimasi'}
"""
        text.insert(tk.END, summary)
        text.config(state=tk.DISABLED)

    def add_financial_tab(self, parent):
        text = tk.Text(parent, wrap=tk.WORD, font=('Consolas', 10))
        text.pack(fill=tk.BOTH, expand=True)
        r = self.result
        panel = PANEL_OPTIONS[r['panel_name']]
        inv = INVERTER_OPTIONS[r['inverter_name']]
        fin = f"""
CAPEX:
  Panel       : {r['panels']} x {panel['power']} Wp @ Rp {panel['price_per_wp']:,.0f}/Wp = Rp {r['panels']*panel['power']*panel['price_per_wp']:,.0f}
  Inverter    : {inv['power_kw']} kW @ Rp {inv['price_per_kw']:,.0f}/kW = Rp {inv['power_kw']*inv['price_per_kw']:,.0f}
  Instalasi   : @ Rp 1.500.000/kWp = Rp {r['dc_kwp']*1500000:,.0f}
  TOTAL CAPEX : Rp {r['capex']:,.0f}

Penghematan tahunan:
  Produksi    : {r['annual_kwh']:.0f} kWh
  Tarif       : Rp 1.500/kWh
  Penghematan kotor: Rp {r['annual_saving']:,.0f}
  O&M (1%)    : Rp {r['o_m']:,.0f}
  Penghematan bersih: Rp {r['net_saving']:,.0f}

Payback period: {r['payback']:.2f} tahun ({r['payback']*12:.1f} bulan)
"""
        text.insert(tk.END, fin)
        text.config(state=tk.DISABLED)

    def add_loss_diagram(self, parent):
        fig = plt.Figure(figsize=(6,4), dpi=100)
        ax = fig.add_subplot(111)
        losses = self.result['losses']
        labels = list(losses.keys())
        values = list(losses.values())
        bars = ax.barh(labels, values, color='salmon')
        ax.set_xlabel("Loss (%)")
        ax.set_title("Loss Diagram")
        for bar in bars:
            w = bar.get_width()
            ax.text(w+0.5, bar.get_y()+bar.get_height()/2, f'{w:.1f}%', va='center')
        ax.set_xlim(0, max(values)+10)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def add_monthly_chart(self, parent):
        fig = plt.Figure(figsize=(9,5), dpi=100)
        ax = fig.add_subplot(111)
        monthly = self.result['monthly_kwh']
        ax.bar(MONTH_NAMES, monthly, color='orange')
        ax.set_title("Produksi Energi per Bulan (kWh)")
        ax.set_ylabel("kWh")
        ax.set_xlabel("Bulan")
        for i, v in enumerate(monthly):
            ax.text(i, v+5, f'{v:.0f}', ha='center', fontsize=8)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def add_params_tab(self, parent):
        text = tk.Text(parent, wrap=tk.WORD, font=('Consolas', 10))
        text.pack(fill=tk.BOTH, expand=True)
        r = self.result
        params = f"""
Lokasi: {r['lat']:.6f}, {r['lon']:.6f}
Tilt: {r['tilt']}°, Azimuth: {r['azimuth']}° (0°=Utara)
Orientasi factor: {r['orientation_factor']:.2f}

Panel: {r['panel_name']} - {PANEL_OPTIONS[r['panel_name']]['power']} Wp, efisiensi {PANEL_OPTIONS[r['panel_name']]['efficiency']*100:.0f}%
Inverter: {r['inverter_name']} - {INVERTER_OPTIONS[r['inverter_name']]['power_kw']} kW

Produksi bulanan (kWh):
"""
        for name, val in zip(MONTH_NAMES, r['monthly_kwh']):
            params += f"  {name}: {val:.0f}\n"
        params += f"\nTOTAL TAHUNAN: {r['annual_kwh']:.0f} kWh"
        text.insert(tk.END, params)
        text.config(state=tk.DISABLED)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if path:
            r = self.result
            data = {
                "Parameter": ["Area terdeteksi (m2)", "Area efektif (m2)", "Jumlah panel", "Kapasitas DC (kWp)",
                              "Energi tahunan (kWh)", "CAPEX (Rp)", "Net saving (Rp/tahun)", "Payback (tahun)"],
                "Nilai": [r['area_detected'], r['area_effective'], r['panels'], r['dc_kwp'],
                          r['annual_kwh'], r['capex'], r['net_saving'], r['payback']]
            }
            df = pd.DataFrame(data)
            df.to_csv(path, index=False)
            messagebox.showinfo("Export", f"Disimpan ke {path}")

    def export_txt(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("ASTROPHAGE PV - LAPORAN PLTS\n")
                f.write(f"Tanggal: {datetime.now()}\n")
                f.write(f"Lokasi: {self.result['lat']:.4f}, {self.result['lon']:.4f}\n")
                f.write(f"Luas efektif: {self.result['area_effective']:.1f} m2\n")
                f.write(f"Kapasitas: {self.result['dc_kwp']:.2f} kWp\n")
                f.write(f"Energi tahunan: {self.result['annual_kwh']:.0f} kWh\n")
                f.write(f"CAPEX: Rp {self.result['capex']:,.0f}\n")
                f.write(f"Payback: {self.result['payback']:.2f} tahun\n")
            messagebox.showinfo("Export", f"Disimpan ke {path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AstrophagePV(root)
    root.mainloop()