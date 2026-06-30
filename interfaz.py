"""
interfaz.py
──────────────────────────────────────────────
Interfaz gráfica para el sistema de encuestas de la guardia.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import date, timedelta

AZUL_OSCURO  = "#1B3A5C"
AZUL_MEDIO   = "#2D5F8A"
CELESTE      = "#5BA4CF"
BLANCO       = "#FFFFFF"
GRIS_FONDO   = "#F0F4F8"
GRIS_TEXTO   = "#4A5568"
GRIS_BORDE   = "#CBD5E0"
VERDE        = "#38A169"
ROJO         = "#E53E3E"
AMARILLO     = "#D69E2E"

FUENTE_TITULO  = ("Segoe UI", 18, "bold")
FUENTE_LABEL   = ("Segoe UI", 10)
FUENTE_INPUT   = ("Segoe UI", 11)
FUENTE_BOTON   = ("Segoe UI", 11, "bold")
FUENTE_TABLA   = ("Segoe UI", 10)
FUENTE_SMALL   = ("Segoe UI", 9)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Guardia Médica · Encuestas")
        self.geometry("900x640")
        self.minsize(780, 580)
        self.configure(bg=GRIS_FONDO)
        self.resizable(True, True)

        try:
            self.iconbitmap("icono.ico")
        except Exception:
            pass

        self._build_ui()
        self._cargar_tabla()

    def _build_ui(self):
        header = tk.Frame(self, bg=AZUL_OSCURO, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🏥  Guardia Médica · Sistema de Encuestas",
            font=FUENTE_TITULO,
            bg=AZUL_OSCURO,
            fg=BLANCO,
        ).pack(side="left", padx=24, pady=14)

        main = tk.Frame(self, bg=GRIS_FONDO)
        main.pack(fill="both", expand=True, padx=20, pady=16)

        left = tk.Frame(main, bg=GRIS_FONDO)
        left.pack(side="left", fill="y", padx=(0, 16))
        left_canvas = tk.Canvas(left, bg=GRIS_FONDO, highlightthickness=0, width=290)
        left_scroll = tk.Scrollbar(left, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_canvas.pack(side="left", fill="both", expand=True)
        left_scroll.pack(side="right", fill="y")
        left_inner = tk.Frame(left_canvas, bg=GRIS_FONDO)
        left_canvas.create_window((0, 0), window=left_inner, anchor="nw", width=280)

        def _ajustar_scroll(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        left_inner.bind("<Configure>", _ajustar_scroll)

        def _mouse_wheel(event):
            left_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        left_canvas.bind("<Enter>", lambda e: left_canvas.bind_all("<MouseWheel>", _mouse_wheel))
        left_canvas.bind("<Leave>", lambda e: left_canvas.unbind_all("<MouseWheel>"))
        self._build_form(left_inner)

        sep = tk.Frame(main, bg=GRIS_BORDE, width=1)
        sep.pack(side="left", fill="y")

        right = tk.Frame(main, bg=GRIS_FONDO)
        right.pack(side="left", fill="both", expand=True, padx=(16, 0))
        self._build_table(right)

        self.status_var = tk.StringVar(value="Listo.")
        status_bar = tk.Label(
            self,
            textvariable=self.status_var,
            bg=AZUL_OSCURO,
            fg=BLANCO,
            font=FUENTE_SMALL,
            anchor="w",
            padx=16,
            pady=6,
        )
        status_bar.pack(fill="x", side="bottom")

    def _build_form(self, parent):
        self._form_frame = parent
        tk.Label(
            parent,
            text="Cargar nuevo paciente",
            font=("Segoe UI", 12, "bold"),
            bg=GRIS_FONDO,
            fg=AZUL_OSCURO,
        ).pack(anchor="w", pady=(0, 12))

        tk.Label(
            parent,
            text="El paciente recibirá un WhatsApp mañana a las 9:00 hs con el link a la encuesta.",
            font=FUENTE_SMALL,
            bg=GRIS_FONDO,
            fg=GRIS_TEXTO,
            wraplength=270,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        self.var_nombre   = tk.StringVar()
        self.var_apellido = tk.StringVar()
        self.var_dni      = tk.StringVar()
        self.var_telefono = tk.StringVar()
        self._paciente_encontrado = None
        self._paciente_editando = None
        self._evitar_busqueda = False

        self._entry_nombre   = self._campo(parent, "Nombre *", self.var_nombre)
        self._entry_apellido = self._campo(parent, "Apellido *", self.var_apellido)
        self._campo(parent, "DNI *", self.var_dni, hint="Ej: 12345678")
        self._campo(parent, "Teléfono celular *", self.var_telefono, hint="Ej: 11 2345-6789")

        self._dni_trace_id = None
        self.var_dni.trace_add("write", self._on_dni_change)

        self.btn_accion = tk.Button(
            parent,
            text="💾  Guardar paciente",
            font=FUENTE_BOTON,
            bg=AZUL_MEDIO,
            fg=BLANCO,
            activebackground=AZUL_OSCURO,
            activeforeground=BLANCO,
            relief="flat",
            cursor="hand2",
            pady=10,
            command=self._guardar,
        )
        self.btn_accion.pack(fill="x", pady=(8, 4))

        tk.Button(
            parent,
            text="✕  Limpiar campos",
            font=FUENTE_SMALL,
            bg=GRIS_FONDO,
            fg=GRIS_TEXTO,
            activebackground=GRIS_BORDE,
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self._limpiar,
        ).pack(fill="x")

        tk.Frame(parent, bg=GRIS_BORDE, height=1).pack(fill="x", pady=20)

        tk.Label(
            parent,
            text="Envío automático",
            font=("Segoe UI", 12, "bold"),
            bg=GRIS_FONDO,
            fg=AZUL_OSCURO,
        ).pack(anchor="w", pady=(0, 8))

        self.lbl_cron = tk.Label(
            parent,
            text="⏸  Cron inactivo",
            font=FUENTE_SMALL,
            bg=GRIS_FONDO,
            fg=ROJO,
        )
        self.lbl_cron.pack(anchor="w", pady=(0, 8))

        self.btn_cron = tk.Button(
            parent,
            text="▶  Iniciar cron (9:00 hs)",
            font=FUENTE_BOTON,
            bg=VERDE,
            fg=BLANCO,
            activebackground="#2F855A",
            activeforeground=BLANCO,
            relief="flat",
            cursor="hand2",
            pady=10,
            command=self._toggle_cron,
        )
        self.btn_cron.pack(fill="x", pady=(0, 4))

        tk.Button(
            parent,
            text="⚡  Enviar ahora (prueba)",
            font=FUENTE_SMALL,
            bg=GRIS_FONDO,
            fg=AZUL_MEDIO,
            activebackground=GRIS_BORDE,
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self._enviar_ahora,
        ).pack(fill="x")

    def _campo(self, parent, label, var, hint=""):
        tk.Label(
            parent, text=label,
            font=FUENTE_LABEL,
            bg=GRIS_FONDO,
            fg=AZUL_OSCURO,
        ).pack(anchor="w", pady=(8, 2))

        frame = tk.Frame(parent, bg=GRIS_BORDE, padx=1, pady=1)
        frame.pack(fill="x")

        entry = tk.Entry(
            frame,
            textvariable=var,
            font=FUENTE_INPUT,
            bg=BLANCO,
            fg=GRIS_TEXTO,
            insertbackground=AZUL_MEDIO,
            relief="flat",
        )
        entry.pack(fill="x", padx=0, pady=0, ipady=8, ipadx=8)

        if hint:
            tk.Label(
                parent, text=hint,
                font=("Segoe UI", 8),
                bg=GRIS_FONDO,
                fg="#A0AEC0",
            ).pack(anchor="w")

        return entry

    def _build_table(self, parent):
        header_row = tk.Frame(parent, bg=GRIS_FONDO)
        header_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            header_row,
            text="Pacientes cargados",
            font=("Segoe UI", 12, "bold"),
            bg=GRIS_FONDO,
            fg=AZUL_OSCURO,
        ).pack(side="left")

        tk.Button(
            header_row,
            text="↻  Actualizar",
            font=FUENTE_SMALL,
            bg=GRIS_FONDO,
            fg=AZUL_MEDIO,
            activebackground=GRIS_BORDE,
            relief="flat",
            cursor="hand2",
            pady=4,
            padx=8,
            command=self._cargar_tabla,
        ).pack(side="right")

        filtro_frame = tk.Frame(parent, bg=GRIS_FONDO)
        filtro_frame.pack(fill="x", pady=(0, 8))

        self.var_filtro = tk.StringVar()
        self.var_filtro.trace_add("write", lambda *_: self._filtrar_tabla())

        tk.Label(filtro_frame, text="🔍", bg=GRIS_FONDO, font=FUENTE_LABEL).pack(side="left")
        f = tk.Frame(filtro_frame, bg=GRIS_BORDE, padx=1, pady=1)
        f.pack(side="left", fill="x", expand=True, padx=4)
        tk.Entry(
            f,
            textvariable=self.var_filtro,
            font=FUENTE_INPUT,
            bg=BLANCO,
            fg=GRIS_TEXTO,
            relief="flat",
        ).pack(fill="x", ipady=5, ipadx=6)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Guardia.Treeview",
            background=BLANCO,
            fieldbackground=BLANCO,
            foreground=GRIS_TEXTO,
            font=FUENTE_TABLA,
            rowheight=32,
        )
        style.configure("Guardia.Treeview.Heading",
            background=AZUL_OSCURO,
            foreground=BLANCO,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map("Guardia.Treeview",
            background=[("selected", CELESTE)],
            foreground=[("selected", BLANCO)],
        )

        cols = ("id", "dni", "nombre", "apellido", "telefono", "fecha", "estado")
        self.tree = ttk.Treeview(
            parent,
            columns=cols,
            show="headings",
            style="Guardia.Treeview",
            selectmode="browse",
        )

        anchos = {"id": 44, "dni": 80, "nombre": 110, "apellido": 110, "telefono": 120, "fecha": 80, "estado": 90}
        headers = {"id": "ID", "dni": "DNI", "nombre": "Nombre", "apellido": "Apellido",
                   "telefono": "Teléfono", "fecha": "Fecha carga", "estado": "Estado"}
        for col in cols:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=anchos[col], anchor="center" if col in ("id","dni","fecha","estado") else "w")

        sb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_fila_seleccionada)

        self.lbl_conteo = tk.Label(
            parent.master if hasattr(parent, 'master') else parent,
            text="",
            font=FUENTE_SMALL,
            bg=GRIS_FONDO,
            fg=GRIS_TEXTO,
        )

    # ── Acciones ───────────────────────────────────────────────────────────
    def _guardar(self):
        nombre   = self.var_nombre.get().strip()
        apellido = self.var_apellido.get().strip()
        dni      = self.var_dni.get().strip()
        telefono = self.var_telefono.get().strip()

        if not nombre:
            self._status("⚠  El nombre es obligatorio.", error=True); return
        if not apellido:
            self._status("⚠  El apellido es obligatorio.", error=True); return
        if not dni:
            self._status("⚠  El DNI es obligatorio.", error=True); return
        if not telefono or len("".join(c for c in telefono if c.isdigit())) < 8:
            self._status("⚠  El teléfono debe tener al menos 8 dígitos.", error=True); return

        self.btn_accion.config(state="disabled", text="Guardando…")
        self.update()

        def _tarea():
            try:
                from base_de_datos import agregar_paciente
                nuevo_id = agregar_paciente(nombre, apellido, telefono, dni)
                self.after(0, lambda: self._guardar_ok(nuevo_id, nombre, apellido))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._guardar_err(msg))

        threading.Thread(target=_tarea, daemon=True).start()

    def _guardar_ok(self, nuevo_id, nombre, apellido):
        self.btn_accion.config(state="normal", text="💾  Guardar paciente")
        self._status(f"✓  Paciente #{nuevo_id} {nombre} {apellido} guardado. WhatsApp se enviará mañana a las 9:00 hs.")
        self._limpiar()
        self._cargar_tabla()

    def _guardar_err(self, msg):
        self.btn_accion.config(state="normal", text="💾  Guardar paciente")
        self._status(f"✗  Error: {msg}", error=True)
        messagebox.showerror("Error al guardar", msg)

    def _reactivar(self):
        paciente = self._paciente_encontrado
        if not paciente:
            return

        telefono = self.var_telefono.get().strip()
        if not telefono or len("".join(c for c in telefono if c.isdigit())) < 8:
            self._status("⚠  El teléfono debe tener al menos 8 dígitos.", error=True)
            return

        self.btn_accion.config(state="disabled", text="Reactivando…")
        self.update()

        def _tarea():
            try:
                from base_de_datos import actualizar_telefono, reactivar_paciente
                if telefono != paciente["telefono"]:
                    actualizar_telefono(paciente["id"], telefono)
                reactivar_paciente(paciente["id"])
                self.after(0, lambda: self._reactivar_ok(paciente["nombre"], paciente["apellido"]))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._guardar_err(msg))

        threading.Thread(target=_tarea, daemon=True).start()

    def _reactivar_ok(self, nombre, apellido):
        self.btn_accion.config(state="normal", text="↻  Reactivar paciente (enviar mañana)")
        self._status(f"✓  {nombre} {apellido} reactivado. Recibirá WhatsApp mañana a las 9:00 hs.")
        self._limpiar()
        self._cargar_tabla()

    def _on_dni_change(self, *args):
        if self._evitar_busqueda or self._paciente_editando:
            return
        if self._dni_trace_id:
            self.after_cancel(self._dni_trace_id)
        self._dni_trace_id = self.after(400, self._buscar_por_dni)

    def _buscar_por_dni(self):
        dni = self.var_dni.get().strip()
        if len(dni) < 6:
            self._restaurar_formulario()
            return

        def _tarea():
            try:
                from base_de_datos import buscar_por_dni
                paciente = buscar_por_dni(dni)
                self.after(0, lambda: self._mostrar_resultado(paciente))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._status(f"✗  Error al buscar DNI: {msg}", error=True))

        threading.Thread(target=_tarea, daemon=True).start()

    def _mostrar_resultado(self, paciente):
        if paciente:
            self._paciente_encontrado = paciente
            self.var_nombre.set(paciente["nombre"])
            self.var_apellido.set(paciente["apellido"])
            self.var_telefono.set(paciente["telefono"])
            self._set_campos_habilitados(False)
            self.btn_accion.config(
                state="normal",
                text="↻  Reactivar paciente (enviar mañana)",
                bg=VERDE,
                activebackground="#2F855A",
                command=self._reactivar,
            )
            self._status(f"✓  Paciente {paciente['nombre']} {paciente['apellido']} encontrado. Reactivalo para enviar mañana.")
        else:
            self._restaurar_formulario()

    def _restaurar_formulario(self):
        self._paciente_encontrado = None
        self._paciente_editando = None
        if not self.var_nombre.get() and not self.var_apellido.get():
            self._set_campos_habilitados(True)
        self.btn_accion.config(
            state="normal",
            text="💾  Guardar paciente",
            bg=AZUL_MEDIO,
            activebackground=AZUL_OSCURO,
            command=self._guardar,
        )

    def _set_campos_habilitados(self, habilitado):
        estado = "normal" if habilitado else "disabled"
        bg = BLANCO if habilitado else GRIS_FONDO
        for entry in (getattr(self, "_entry_nombre", None), getattr(self, "_entry_apellido", None)):
            if entry:
                entry.config(state=estado, bg=bg)

    def _limpiar(self):
        self.var_nombre.set("")
        self.var_apellido.set("")
        self.var_dni.set("")
        self.var_telefono.set("")
        self._restaurar_formulario()
        self._status("Campos limpiados.")

    def _cargar_tabla(self):
        self._status("Cargando pacientes…")

        def _tarea():
            try:
                from base_de_datos import listar_todos
                data = listar_todos()
                self.after(0, lambda: self._poblar_tabla(data))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._status(f"✗  Error al cargar tabla: {msg}", error=True))

        threading.Thread(target=_tarea, daemon=True).start()

    def _poblar_tabla(self, data):
        self._datos_tabla = data
        self._filtrar_tabla()
        self._status(f"Listo. {len(data)} pacientes en la base de datos.")

    def _filtrar_tabla(self):
        filtro = self.var_filtro.get().lower().strip()
        datos  = getattr(self, "_datos_tabla", [])

        for row in self.tree.get_children():
            self.tree.delete(row)

        hoy  = date.today().isoformat()
        ayer = (date.today() - timedelta(days=1)).isoformat()

        for p in datos:
            nombre_completo = f"{p['nombre']} {p['apellido']}".lower()
            if filtro and filtro not in nombre_completo and filtro not in p["telefono"].lower() and filtro not in str(p.get("dni", "")).lower():
                continue

            fecha = p["fecha_carga"]
            if fecha == hoy:
                fecha_txt = "Hoy"
            elif fecha == ayer:
                fecha_txt = "Ayer"
            else:
                try:
                    from datetime import datetime
                    fecha_txt = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    fecha_txt = fecha

            estado = "✓ Enviado" if p["mensaje_enviado"] else "⏳ Pendiente"
            tag    = "enviado"   if p["mensaje_enviado"] else "pendiente"

            self.tree.insert("", "end", values=(
                p["id"],
                p.get("dni", ""),
                p["nombre"],
                p["apellido"],
                p["telefono"],
                fecha_txt,
                estado,
            ), tags=(tag,))

        self.tree.tag_configure("enviado",   foreground=VERDE)
        self.tree.tag_configure("pendiente", foreground=AMARILLO)

    def _on_fila_seleccionada(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        paciente_id = item["values"][0]

        def _tarea():
            try:
                from base_de_datos import listar_todos
                data = listar_todos()
                paciente = next((p for p in data if p["id"] == paciente_id), None)
                if paciente:
                    self.after(0, lambda: self._cargar_paciente_a_formulario(paciente))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._status(f"✗  Error: {msg}", error=True))

        threading.Thread(target=_tarea, daemon=True).start()

    def _cargar_paciente_a_formulario(self, paciente):
        self._paciente_encontrado = None
        self._paciente_editando = paciente
        self._evitar_busqueda = True
        self.var_nombre.set(paciente["nombre"])
        self.var_apellido.set(paciente["apellido"])
        self.var_dni.set(paciente.get("dni", "") or "")
        self.var_telefono.set(paciente["telefono"])
        self._evitar_busqueda = False
        self._set_campos_habilitados(True)
        self.btn_accion.config(
            state="normal",
            text="✎  Actualizar paciente",
            bg=AZUL_MEDIO,
            activebackground=AZUL_OSCURO,
            command=self._actualizar,
        )
        self._status(f"Editando paciente #{paciente['id']} — {paciente['nombre']} {paciente['apellido']}")

    def _actualizar(self):
        paciente = self._paciente_editando
        if not paciente:
            return

        nombre   = self.var_nombre.get().strip()
        apellido = self.var_apellido.get().strip()
        dni      = self.var_dni.get().strip()
        telefono = self.var_telefono.get().strip()

        if not nombre:
            self._status("⚠  El nombre es obligatorio.", error=True); return
        if not apellido:
            self._status("⚠  El apellido es obligatorio.", error=True); return
        if not dni:
            self._status("⚠  El DNI es obligatorio.", error=True); return
        if not telefono or len("".join(c for c in telefono if c.isdigit())) < 8:
            self._status("⚠  El teléfono debe tener al menos 8 dígitos.", error=True); return

        self.btn_accion.config(state="disabled", text="Actualizando…")
        self.update()

        def _tarea():
            try:
                from base_de_datos import actualizar_paciente
                actualizar_paciente(paciente["id"], dni, nombre, apellido, telefono)
                self.after(0, lambda: self._actualizar_ok(nombre, apellido))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._guardar_err(msg))

        threading.Thread(target=_tarea, daemon=True).start()

    def _actualizar_ok(self, nombre, apellido):
        self.btn_accion.config(state="normal")
        self._status(f"✓  {nombre} {apellido} actualizado. WhatsApp se enviará mañana a las 9:00 hs.")
        self._limpiar()
        self._cargar_tabla()

    # ── Cron ───────────────────────────────────────────────────────────────
    _cron_activo = False
    _cron_thread = None

    def _toggle_cron(self):
        if not self._cron_activo:
            self._iniciar_cron()
        else:
            self._detener_cron()

    def _iniciar_cron(self):
        import schedule, time

        schedule.clear()
        schedule.every().day.at("09:00").do(self._enviar_a_todos_cron)

        self._cron_activo = True
        self.lbl_cron.config(text="▶  Cron activo — próximo envío a las 09:00", fg=VERDE)
        self.btn_cron.config(text="⏹  Detener cron", bg=ROJO, activebackground="#C53030")
        self._status("Cron iniciado. Enviará mensajes todos los días a las 9:00 hs.")

        def _loop():
            while self._cron_activo:
                schedule.run_pending()
                time.sleep(20)

        self._cron_thread = threading.Thread(target=_loop, daemon=True)
        self._cron_thread.start()

    def _detener_cron(self):
        self._cron_activo = False
        self.lbl_cron.config(text="⏸  Cron inactivo", fg=ROJO)
        self.btn_cron.config(text="▶  Iniciar cron (9:00 hs)", bg=VERDE, activebackground="#2F855A")
        self._status("Cron detenido.")

    def _enviar_a_todos_cron(self):
        self.after(0, lambda: self._status("⚡  Cron: iniciando envío automático…"))
        self._ejecutar_envio(modo_cron=True)

    def _enviar_ahora(self):
        if not messagebox.askyesno(
            "Envío de prueba",
            "Se van a enviar WhatsApp a TODOS los pacientes de ayer que no recibieron mensaje.\n\n¿Querés continuar?"
        ):
            return
        self._ejecutar_envio(modo_cron=False)

    def _ejecutar_envio(self, modo_cron=False):
        def _tarea():
            try:
                from enviar_encuestas import enviar_a_todos
                import io, sys, re
                buf = io.StringIO()
                old_stdout = sys.stdout
                sys.stdout = buf
                enviar_a_todos()
                sys.stdout = old_stdout
                salida = buf.getvalue()
                lineas = [l.strip() for l in salida.splitlines() if l.strip()]
                msg = lineas[-1] if lineas else "Envío completado."
                msg = re.sub(r'\033\[[0-9;]*m', '', msg)
                self.after(0, lambda: self._status(f"✓  {msg}"))
                self.after(0, self._cargar_tabla)
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._status(f"✗  Error en envío: {msg}", error=True))
                self.after(0, lambda: messagebox.showerror("Error de envío", msg))

        threading.Thread(target=_tarea, daemon=True).start()
        self._status("⚡  Enviando mensajes por WhatsApp… no cierres la ventana.")

    def _status(self, msg, error=False):
        self.status_var.set(msg)
        self.configure(bg=GRIS_FONDO)


if __name__ == "__main__":
    app = App()
    app.mainloop()