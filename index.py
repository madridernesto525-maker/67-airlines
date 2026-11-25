from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


# Definición de la clase Vuelo
class Vuelo:
    def __init__(self, codigo, origen, destino, horario, hora_llegada, precio_base):
        self.codigo = codigo
        self.origen = origen
        self.destino = destino
        self.horario = horario
        self.hora_llegada = hora_llegada
        self.precio_base = precio_base
        self.economica = {f"ECO{i+1}": True for i in range(10)}
        self.max = {f"MAX{i+1}": True for i in range(6)}
        self.premium = {f"PRE{i+1}": True for i in range(4)}

    def asientos_libres_economica(self):
        return sum(self.economica.values())

    def asientos_libres_max(self):
        return sum(self.max.values())

    def asientos_libres_premium(self):
        return sum(self.premium.values())

    def _obtener_diccionario_y_multiplicador(self, categoria):
        if categoria == "economica":
            return self.economica, 1.0
        elif categoria == "max":
            return self.max, 1.35
        elif categoria == "premium":
            return self.premium, 1.75
        return None, 0

    def calcular_precio(self, categoria, asiento):
        asientos, multiplicador = self._obtener_diccionario_y_multiplicador(categoria)
        if asientos and asientos.get(asiento):
            return True, round(self.precio_base * multiplicador, 2)
        return False, 0

    def reservar(self, categoria, asiento):
        asientos, multiplicador = self._obtener_diccionario_y_multiplicador(categoria)
        if asientos and asientos.get(asiento):
            asientos[asiento] = False  # Ocupar asiento definitivamente
            return True, round(self.precio_base * multiplicador, 2)
        return False, 0


# Definición de la clase SistemaVuelos
class SistemaVuelos:
    def __init__(self):
        self.vuelos = [
            # Tijuana <-> Guadalajara (Duración: ~3h 05m | Diferencia horaria: +2h en GDL)
            Vuelo("67-101", "Tijuana (TIJ)", "Guadalajara (GDL)", "05:00 AM", "10:05 AM", 1900.00),
            Vuelo("67-102", "Tijuana (TIJ)", "Guadalajara (GDL)", "02:00 PM", "07:05 PM", 2100.00),
            Vuelo("67-103", "Guadalajara (GDL)", "Tijuana (TIJ)", "10:00 AM", "11:05 AM", 1900.00),
            Vuelo("67-104", "Guadalajara (GDL)", "Tijuana (TIJ)", "06:00 PM", "07:05 PM", 2100.00),

            # Tijuana <-> Monterrey (Duración: ~2h 55m | Diferencia horaria: +2h en MTY)
            Vuelo("67-201", "Tijuana (TIJ)", "Monterrey (MTY)", "08:00 AM", "12:55 PM", 1500.00),
            Vuelo("67-202", "Tijuana (TIJ)", "Monterrey (MTY)", "07:00 PM", "11:55 PM", 1800.00),
            Vuelo("67-203", "Monterrey (MTY)", "Tijuana (TIJ)", "10:00 AM", "10:55 AM", 1500.00),
            Vuelo("67-204", "Monterrey (MTY)", "Tijuana (TIJ)", "06:00 PM", "06:55 PM", 1800.00),

            # Tijuana <-> Ciudad de Mexico (Duración: ~3h 30m | Diferencia horaria: +2h en MEX)
            Vuelo("67-301", "Tijuana (TIJ)", "Ciudad de Mexico (MEX)", "06:00 AM", "11:30 AM", 2200.00),
            Vuelo("67-302", "Tijuana (TIJ)", "Ciudad de Mexico (MEX)", "05:30 PM", "11:00 PM", 2500.00),
            Vuelo("67-303", "Ciudad de Mexico (MEX)", "Tijuana (TIJ)", "02:00 PM", "03:30 PM", 2200.00),
            Vuelo("67-304", "Ciudad de Mexico (MEX)", "Tijuana (TIJ)", "10:00 PM", "11:30 PM", 2500.00),
        ]

    def buscar_vuelo(self, codigo):
        for v in self.vuelos:
            if v.codigo == codigo:
                return v
        return None


sistema = SistemaVuelos()


def parsear_float(valor, default=0.0):
    try:
        return float(valor) if valor not in (None, "") else float(default)
    except ValueError:
        return float(default)


def obtener_info_tramos(vuelo_actual, precio_actual, vuelo_ida_cod, vuelo_regreso_cod, p_ida_raw=None, p_reg_raw=None):
    obj_ida = sistema.buscar_vuelo(vuelo_ida_cod) if vuelo_ida_cod else None
    obj_regreso = sistema.buscar_vuelo(vuelo_regreso_cod) if vuelo_regreso_cod else None

    if not obj_ida and vuelo_actual:
        obj_ida = vuelo_actual

    es_redondo = bool(obj_ida and obj_regreso and obj_ida.codigo != obj_regreso.codigo)

    if es_redondo:
        precio_ida = parsear_float(p_ida_raw, obj_ida.precio_base)
        precio_regreso = parsear_float(p_reg_raw, obj_regreso.precio_base)

        # Si no venían explícitos en la petición, actualizar el tramo correspondiente
        if p_ida_raw in (None, "") and vuelo_actual and vuelo_actual.codigo == obj_ida.codigo:
            precio_ida = float(precio_actual)
        if p_reg_raw in (None, "") and vuelo_actual and vuelo_actual.codigo == obj_regreso.codigo:
            precio_regreso = float(precio_actual)

        precio_total = round(precio_ida + precio_regreso, 2)
    else:
        precio_ida = parsear_float(p_ida_raw, precio_actual)
        precio_regreso = 0.0
        precio_total = round(precio_ida, 2)

    return obj_ida, obj_regreso, precio_ida, precio_regreso, precio_total, es_redondo


# ----------------- RUTAS DE FLASK -----------------

@app.route("/")
def principal():
    return render_template("index.html")


@app.route("/vuelos")
def ver_vuelos():
    tipo_vuelo = request.args.get("tipo_vuelo")
    origen = request.args.get("origen", "").strip().lower()
    destino = request.args.get("destino", "").strip().lower()
    fecha_ida = request.args.get("fecha_ida")
    fecha_regreso = request.args.get("fecha_regreso")
    pasajeros = request.args.get("pasajeros", 1)
    paso = request.args.get("paso", "ida")
    vuelo_ida = request.args.get("vuelo_ida", "")

    if tipo_vuelo == "redondo" and paso == "regreso":
        origen_actual = destino
        destino_actual = origen
        fecha_actual = fecha_regreso
    else:
        origen_actual = origen
        destino_actual = destino
        fecha_actual = fecha_ida

    if "monterrey" in destino_actual or "mty" in destino_actual:
        imagen_fondo = "monterrey.jpg"
    elif "guadalajara" in destino_actual or "gdl" in destino_actual:
        imagen_fondo = "guadalajara.webp"
    elif "tijuana" in destino_actual or "tij" in destino_actual:
        imagen_fondo = "tijuana.jpg"
    elif "ciudad de mexico" in destino_actual or "mex" in destino_actual:
        imagen_fondo = "cdmx.webp"
    else:
        imagen_fondo = "cdmx.webp"

    if origen_actual and destino_actual:
        vuelos_filtrados = [
            v for v in sistema.vuelos
            if origen_actual in v.origen.lower() and destino_actual in v.destino.lower()
        ]
    else:
        vuelos_filtrados = sistema.vuelos

    return render_template(
        "vuelos.html",
        vuelos=vuelos_filtrados,
        tipo_vuelo=tipo_vuelo,
        origen=origen,
        destino=destino,
        origen_actual=origen_actual,
        destino_actual=destino_actual,
        fecha_ida=fecha_ida,
        fecha_regreso=fecha_regreso,
        fecha_actual=fecha_actual,
        pasajeros=pasajeros,
        paso=paso,
        vuelo_ida=vuelo_ida,
        imagen_fondo=imagen_fondo,
    )


@app.route("/reservar/<codigo>", methods=["GET", "POST"])
def reservar_vuelo(codigo):
    vuelo = sistema.buscar_vuelo(codigo)
    if not vuelo:
        return "Vuelo no encontrado", 404

    vuelo_ida = request.args.get("vuelo_ida") or request.form.get("vuelo_ida", "")
    vuelo_regreso = request.args.get("vuelo_regreso") or request.form.get("vuelo_regreso", "")
    asiento_ida = request.args.get("asiento_ida") or request.form.get("asiento_ida", "")
    categoria_ida = request.args.get("categoria_ida") or request.form.get("categoria_ida", "")
    precio_ida = request.args.get("precio_ida") or request.form.get("precio_ida", "")
    mensaje = None

    if request.method == "POST":
        categoria = request.form.get("categoria", "").strip().lower()
        asiento = request.form.get("asiento", "").strip().upper()

        # Validamos disponibilidad y precio SIN bloquear el asiento todavía (se bloquea al pagar)
        disponible, precio = vuelo.calcular_precio(categoria, asiento)

        if disponible:
            es_redondo = bool(vuelo_ida and vuelo_regreso and vuelo_ida != vuelo_regreso)

            # Si es vuelo redondo y apenas elegimos el asiento de IDA, pasamos a elegir el asiento de REGRESO
            if es_redondo and vuelo.codigo == vuelo_ida:
                return redirect(
                    url_for(
                        "reservar_vuelo",
                        codigo=vuelo_regreso,
                        vuelo_ida=vuelo_ida,
                        vuelo_regreso=vuelo_regreso,
                        asiento_ida=asiento,
                        categoria_ida=categoria,
                        precio_ida=precio,
                    )
                )

            # Si es viaje sencillo o ya terminamos de elegir el asiento de REGRESO:
            if es_redondo:
                asiento_regreso = asiento
                categoria_regreso = categoria
                precio_regreso = precio
            else:
                asiento_ida = asiento
                categoria_ida = categoria
                precio_ida = precio
                asiento_regreso = ""
                categoria_regreso = ""
                precio_regreso = 0

            return redirect(
                url_for(
                    "datos_pasajero",
                    codigo=vuelo.codigo,
                    categoria=categoria,
                    asiento=asiento,
                    precio=precio,
                    vuelo_ida=vuelo_ida or vuelo.codigo,
                    vuelo_regreso=vuelo_regreso,
                    asiento_ida=asiento_ida,
                    categoria_ida=categoria_ida,
                    precio_ida=precio_ida,
                    asiento_regreso=asiento_regreso,
                    categoria_regreso=categoria_regreso,
                    precio_regreso=precio_regreso,
                )
            )
        else:
            mensaje = "Error: Asiento inválido, ya está ocupado o no seleccionado correctamente."

    return render_template(
        "reservar.html",
        vuelo=vuelo,
        mensaje=mensaje,
        vuelo_ida=vuelo_ida,
        vuelo_regreso=vuelo_regreso,
        asiento_ida=asiento_ida,
        categoria_ida=categoria_ida,
        precio_ida=precio_ida,
    )


@app.route("/pasajero/<codigo>", methods=["GET", "POST"])
def datos_pasajero(codigo):
    vuelo = sistema.buscar_vuelo(codigo)
    if not vuelo:
        return "Vuelo no encontrado", 404

    datos = request.values  # Lee tanto args (GET) como form (POST)
    categoria = datos.get("categoria", "economica").strip().lower()
    asiento = datos.get("asiento", "").strip().upper()
    precio = parsear_float(datos.get("precio"), vuelo.precio_base)

    vuelo_ida = datos.get("vuelo_ida", "")
    vuelo_regreso = datos.get("vuelo_regreso", "")
    asiento_ida = datos.get("asiento_ida", asiento).strip().upper()
    categoria_ida = datos.get("categoria_ida", categoria).strip().lower()
    asiento_regreso = datos.get("asiento_regreso", "").strip().upper()
    categoria_regreso = datos.get("categoria_regreso", "").strip().lower()

    obj_ida, obj_regreso, precio_ida, precio_regreso, precio_total, es_redondo = obtener_info_tramos(
        vuelo, precio, vuelo_ida, vuelo_regreso, datos.get("precio_ida"), datos.get("precio_regreso")
    )

    if request.method == "POST":
        pasajero = {
            "nombre": request.form.get("nombre", "").strip(),
            "apellido": request.form.get("apellido", "").strip(),
            "fecha_nacimiento": request.form.get("fecha_nacimiento", "").strip(),
            "correo": request.form.get("correo", "").strip(),
            "telefono": request.form.get("telefono", "").strip(),
            "documento": request.form.get("documento", "").strip(),
        }
        return render_template(
            "pago.html",
            vuelo=vuelo,
            categoria=categoria,
            asiento=asiento,
            precio=precio,
            pasajero=pasajero,
            vuelo_ida=vuelo_ida,
            vuelo_regreso=vuelo_regreso,
            asiento_ida=asiento_ida,
            categoria_ida=categoria_ida,
            asiento_regreso=asiento_regreso,
            categoria_regreso=categoria_regreso,
            obj_ida=obj_ida,
            obj_regreso=obj_regreso,
            precio_ida=precio_ida,
            precio_regreso=precio_regreso,
            precio_total=precio_total,
            es_redondo=es_redondo,
        )

    return render_template(
        "pasajero.html",
        vuelo=vuelo,
        categoria=categoria,
        asiento=asiento,
        precio=precio,
        vuelo_ida=vuelo_ida,
        vuelo_regreso=vuelo_regreso,
        asiento_ida=asiento_ida,
        categoria_ida=categoria_ida,
        asiento_regreso=asiento_regreso,
        categoria_regreso=categoria_regreso,
        obj_ida=obj_ida,
        obj_regreso=obj_regreso,
        precio_ida=precio_ida,
        precio_regreso=precio_regreso,
        precio_total=precio_total,
        es_redondo=es_redondo,
    )


@app.route("/pago/<codigo>", methods=["POST"])
def procesar_pago(codigo):
    vuelo = sistema.buscar_vuelo(codigo)
    if not vuelo:
        return "Vuelo no encontrado", 404

    categoria = request.form.get("categoria", "economica").strip().lower()
    asiento = request.form.get("asiento", "").strip().upper()
    precio = parsear_float(request.form.get("precio"), vuelo.precio_base)

    vuelo_ida = request.form.get("vuelo_ida", "")
    vuelo_regreso = request.form.get("vuelo_regreso", "")
    asiento_ida = request.form.get("asiento_ida", asiento).strip().upper()
    categoria_ida = request.form.get("categoria_ida", categoria).strip().lower()
    asiento_regreso = request.form.get("asiento_regreso", "").strip().upper()
    categoria_regreso = request.form.get("categoria_regreso", "").strip().lower()

    obj_ida, obj_regreso, precio_ida, precio_regreso, precio_total, es_redondo = obtener_info_tramos(
        vuelo, precio, vuelo_ida, vuelo_regreso, request.form.get("precio_ida"), request.form.get("precio_regreso")
    )

    # Ocupar definitivamente los asientos al confirmar el pago
    if obj_ida and asiento_ida:
        obj_ida.reservar(categoria_ida or categoria, asiento_ida)
    if es_redondo and obj_regreso and asiento_regreso:
        obj_regreso.reservar(categoria_regreso or categoria, asiento_regreso)

    pasajero = {
        "nombre": request.form.get("nombre", "").strip(),
        "apellido": request.form.get("apellido", "").strip(),
        "fecha_nacimiento": request.form.get("fecha_nacimiento", "").strip(),
        "correo": request.form.get("correo", "").strip(),
        "telefono": request.form.get("telefono", "").strip(),
        "documento": request.form.get("documento", "").strip(),
    }

    numero_tarjeta = request.form.get("numero_tarjeta", "").strip()
    pago = {
        "banco": request.form.get("banco", "Banco ").strip(),
        "titular": request.form.get("titular", "").strip(),
        "numero_tarjeta": numero_tarjeta,
        "vencimiento": request.form.get("vencimiento", "").strip(),
    }

    return render_template(
        "confirmacion.html",
        vuelo=vuelo,
        categoria=categoria,
        asiento=asiento,
        precio=precio,
        pasajero=pasajero,
        pago=pago,
        vuelo_ida=vuelo_ida,
        vuelo_regreso=vuelo_regreso,
        asiento_ida=asiento_ida,
        categoria_ida=categoria_ida,
        asiento_regreso=asiento_regreso,
        categoria_regreso=categoria_regreso,
        obj_ida=obj_ida,
        obj_regreso=obj_regreso,
        precio_ida=precio_ida,
        precio_regreso=precio_regreso,
        precio_total=precio_total,
        es_redondo=es_redondo,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=5067)