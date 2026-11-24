# Módulo de datos y lógica del chatbot de colectivos de Abra Pampa.
# Centraliza destinos, horarios, precios, contactos y el modelo de lenguaje usado por la app.
import re  # Permite buscar patrones de texto con expresiones regulares.
from difflib import SequenceMatcher  # Compara la similitud entre palabras para tolerar errores leves.
import unicodedata  # Permite quitar acentos y normalizar cadenas de texto.
from dataclasses import dataclass  # Permite crear clases simples para guardar datos.
from datetime import datetime  # Permite trabajar con fechas y horas.

# scikit-learn proporciona las herramientas de aprendizaje automático del asistente.
from sklearn.feature_extraction.text import TfidfVectorizer  # Convierte frases en valores numéricos TF-IDF.
from sklearn.linear_model import LogisticRegression  # Clasifica cada frase en una intención.

# ZONAS guarda los destinos y los horarios habituales de cada empresa, separados por zona.
ZONAS = {
    "sur": {  # Zona sur: localidades hacia el sur desde Abra Pampa.
        "titulo": "HACIA EL SUR",  # Título que se muestra para esta zona.
        "destinos": ["Tres Cruces", "Humahuaca", "Tilcara", "Volcán", "León", "San Salvador de Jujuy",
                     "Yala", "Maimará", "Purmamarca", "Tumbaya"],  # Destinos atendidos en la zona.
        "horarios": {  # Horarios de semana por empresa.
            "Evelia": ["13:30"],  # Salidas de Evelia.
            "Jama": ["07:45", "14:30", "18:00", "20:00", "23:00"],  # Salidas de Jama.
            "Panamericano": ["08:15", "10:00", "11:40", "14:00", "14:15", "15:00", "17:00", "19:00",
                             "20:30", "22:00", "00:00", "03:45"],  # Salidas de Panamericano.
            "Quiaqueño": ["10:30", "12:00", "13:30", "15:30", "18:20", "20:15", "22:20", "00:30", "04:20"],  # Salidas de Quiaqueño.
            "Balut": ["01:00", "09:50", "12:15", "16:10"],  # Salidas de Balut.
        },
    },
    "norte": {  # Zona norte: localidades hacia el norte desde Abra Pampa.
        "titulo": "HACIA EL NORTE",  # Título que se muestra para esta zona.
        "destinos": ["Puesto del Marqués", "La Intermedia", "Pumahuasi", "La Quiaca"],  # Destinos atendidos en la zona.
        "horarios": {  # Horarios de semana por empresa.
            "Evelia": ["17:15"],  # Salidas de Evelia.
            "Jama": ["03:00", "08:00", "09:45", "14:00", "20:00"],  # Salidas de Jama.
            "Panamericano": ["05:45", "08:30", "09:50", "11:30", "12:50", "15:00", "18:30", "21:50", "23:30"],  # Salidas de Panamericano.
            "Quiaqueño": ["03:00", "04:30", "06:30", "10:30", "13:00", "15:45", "17:15", "21:50", "00:30"],  # Salidas de Quiaqueño.
            "Balut": ["04:00", "06:00", "11:30", "16:30", "21:30"],  # Salidas de Balut.
        },
    },
}

# HORARIOS_FINDE guarda los horarios reducidos de fin de semana y feriados.
HORARIOS_FINDE = {
    "sur": {  # Horarios reducidos hacia el sur.
        "Evelia": ["14:00"], "Jama": ["08:00", "15:00", "20:00"],
        "Panamericano": ["09:00", "13:00", "18:00", "21:00"],
        "Quiaqueño": ["11:00", "16:00", "21:00"], "Balut": ["10:00", "17:00"],
    },
    "norte": {  # Horarios reducidos hacia el norte.
        "Evelia": ["17:30"], "Jama": ["08:30", "15:00", "20:00"],
        "Panamericano": ["09:00", "14:00", "19:00"],
        "Quiaqueño": ["07:00", "14:00", "20:00"], "Balut": ["07:00", "16:00"],
    },
}

# DURACION_MIN indica la duración estimada de viaje en minutos para cada destino.
DURACION_MIN = {
    "Tres Cruces": 20, "Humahuaca": 60, "Tilcara": 90, "Maimará": 75,  # Destinos de la zona sur.
    "Purmamarca": 100, "Tumbaya": 110, "Volcán": 130, "Yala": 150,  # Destinos de la zona sur.
    "León": 160, "San Salvador de Jujuy": 180,  # Destinos lejanos de la zona sur.
    "Puesto del Marqués": 25, "La Intermedia": 45, "Pumahuasi": 70, "La Quiaca": 90,  # Destinos de la zona norte.
}

# FERIADOS_2026 contiene los feriados argentinos del año en formato mes-día.
FERIADOS_2026 = {
    "01-01": "Año Nuevo", "02-16": "Carnaval", "02-17": "Carnaval",
    "03-24": "Día de la Memoria", "04-02": "Malvinas", "04-03": "Viernes Santo",
    "05-01": "Día del Trabajador", "05-25": "Revolución de Mayo",
    "06-20": "Día de la Bandera", "07-09": "Día de la Independencia",
    "08-17": "San Martín", "10-12": "Día de la Diversidad", "11-20": "Soberanía Nacional",
    "12-08": "Inmaculada Concepción", "12-25": "Navidad",
}

# PRECIOS guarda el valor de un boleto por destino; el precio es igual en todas las empresas.
PRECIOS = {
    "Tres Cruces": "$2.000", "Humahuaca": "$9.000", "Tilcara": "$13.000", "León": "$19.500",
    "San Salvador de Jujuy": "$21.300", "Puesto del Marqués": "$1.800", "La Intermedia": "$3.200",
    "Pumahuasi": "$4.800", "La Quiaca": "$6.200", "Yala": "$20.500", "Maimará": "$13.800",
    "Purmamarca": "$14.500", "Tumbaya": "$16.000", "Volcán": "$17.500",
}

# CONTACTOS asocia cada empresa con su número de teléfono.
CONTACTOS = {
    "Balut": "3886065780", "Evelia": "3885123456", "Jama": "3885234567",
    "Panamericano": "3885345678", "Quiaqueño": "3885456789",
}

EMPRESAS_ENVIOS = ["Balut", "Quiaqueño", "Evelia"]  # Empresas que realizan envíos y encomiendas.
HORARIO_BOLETERIA = "de 06:00 a 23:00 hs"  # Horario de atención de la boletería.

# ALIAS_DESTINOS permite reconocer formas abreviadas o populares de nombrar destinos.
ALIAS_DESTINOS = {
    "humahu": "Humahuaca", "cruces": "Tres Cruces", "cruses": "Tres Cruces", "ticara": "Tilcara",
    "jujuy": "San Salvador de Jujuy", "juju": "San Salvador de Jujuy",
    "salvador": "San Salvador de Jujuy", "marques": "Puesto del Marqués",
    "quiaca": "La Quiaca", "intermedia": "La Intermedia",
}

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]  # Nombres de los días.

MSG_DESPEDIDA = "Muchas gracias por utilizar el asistente de colectivos de Abra Pampa."  # Texto final.
MSG_NO_ENTENDIDO = ("No se ha podido comprender la consulta. Puede consultar por horarios, próximos colectivos, "  # Respuesta cuando no se entiende.
                    "precios, forma de pago, comparación de empresas, terminal, envíos o contactos.")
MSG_PEDIR_DESTINO_COMPARAR = "¿A qué destino desea comparar?"  # Pide un destino para comparar.
MSG_NOTA_REDUCIDO = "Nota: Horarios reducidos de fin de semana / feriado."  # Aviso de horarios reducidos.


def ahora():  # Devuelve la fecha y hora actuales del sistema.
    return datetime.now()  # Crea un objeto datetime con el momento actual.


def normalizar(texto):  # Deja un texto sin acentos, en minúsculas y sin signos de puntuación.
    texto = unicodedata.normalize("NFD", texto.lower().strip())  # Minúsculas y separa acentos.
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")  # Quita las marcas de acento.
    texto = re.sub(r"[^\w\s]", " ", texto)  # Reemplaza signos por espacios.
    return " ".join(texto.split())  # Une espacios repetidos en uno solo.


def contiene(texto, palabras):  # Indica si el texto incluye alguna de las palabras dadas.
    return any(palabra in texto for palabra in palabras)  # Busca cada palabra y devuelve True si encuentra una.


def palabras_cercanas(token, palabra, umbral=0.78):  # Detecta abreviaturas y errores leves en una palabra.
    if len(token) < 4 or len(palabra) < 4:  # Ignora textos muy cortos para evitar falsos positivos.
        return False  # No hay suficiente información para comparar.
    if token.startswith(palabra) or palabra.startswith(token):  # Reconoce prefijos como "horar" o "preci".
        return True  # La coincidencia por prefijo es suficiente.
    return SequenceMatcher(None, token, palabra).ratio() >= umbral  # Compara similitud con un umbral alto.


def contiene_tolerante(texto, palabras):  # Busca palabras clave admitiendo abreviaturas y errores leves.
    if contiene(texto, palabras):  # Primero intenta la coincidencia exacta de siempre.
        return True  # La palabra clave aparece directamente.
    tokens = texto.split()  # Separa la frase normalizada en palabras.
    for palabra in palabras:  # Recorre las palabras clave de la regla.
        clave = normalizar(palabra)  # Normaliza la clave para comparar acentos y signos.
        if " " in clave:  # Las frases completas ya se probaron con contiene().
            continue  # Pasa a la siguiente clave.
        for token in tokens:  # Recorre cada palabra de la consulta del usuario.
            if palabras_cercanas(token, clave):  # Si la palabra es cercana a la clave...
                return True  # La regla se considera cumplida.
    return False  # Ninguna palabra se parece lo suficiente.




def con_y(lista):  # Une una lista en texto usando comas y la palabra "y".
    return lista[0] if len(lista) == 1 else ", ".join(lista[:-1]) + " y " + lista[-1]  # Devuelve la frase unida.


def a_min(hora):  # Convierte una hora "HH:MM" a minutos desde medianoche.
    hora_salida, minuto_salida = hora.split(":")  # Separa horas y minutos.
    return int(hora_salida) * 60 + int(minuto_salida)  # Calcula el total de minutos.


def sumar_minutos(hora, minutos):  # Suma minutos a una hora y devuelve el resultado en formato "HH:MM".
    total = a_min(hora) + minutos  # Convierte la hora a minutos y realiza la suma.
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"  # Recalcula horas y minutos con vuelta de 24 hs.


def formatear_duracion(minutos):  # Convierte minutos a texto legible, por ejemplo "1h 30min".
    if minutos < 60:  # Si dura menos de una hora, muestra solo minutos.
        return f"{minutos} min"  # Devuelve la duración en minutos.
    horas, resto = divmod(minutos, 60)  # Divide el total en horas y minutos restantes.
    return f"{horas}h {resto:02d}min" if resto else f"{horas}h"  # Muestra horas y minutos o solo horas.


def precio_a_numero(precio_str):  # Convierte un precio como "$13.000" en el número 13000.
    return int(precio_str.replace("$", "").replace(".", "").strip())  # Quita símbolos y convierte a entero.


def formatear_precio(numero):  # Convierte 13000 en "$13.000".
    return f"${numero:,}".replace(",", ".")  # Agrega separador de miles con formato argentino.


# NUMEROS_PALABRA permite entender cantidades escritas con palabras o dígitos.
NUMEROS_PALABRA = {"uno": 1, "1": 1, "dos": 2, "2": 2, "tres": 3, "3": 3, "cuatro": 4, "4": 4,
                   "cinco": 5, "5": 5, "seis": 6, "6": 6}


def detectar_cantidad(f):  # Busca una cantidad de boletos en una frase normalizada.
    coincidencia = re.search(r"\b(uno|dos|tres|cuatro|cinco|seis|1|2|3|4|5|6)\b", f)  # Busca números.
    if coincidencia:  # Si encontró una cantidad...
        return NUMEROS_PALABRA[coincidencia.group(1)]  # Devuelve el valor numérico correspondiente.
    return None  # Si no hay cantidad, devuelve None.


def nombre_dia(fecha=None):  # Devuelve el nombre del día de una fecha; por defecto usa hoy.
    return DIAS[(fecha or ahora()).weekday()]  # weekday() devuelve 0 para lunes y 6 para domingo.


def feriado_de(fecha=None):  # Devuelve el nombre del feriado de una fecha, o None si no lo es.
    return FERIADOS_2026.get((fecha or ahora()).strftime("%m-%d"))  # Busca por mes y día.


def es_fin_de_semana(fecha=None):  # Indica si la fecha cae en sábado o domingo.
    return (fecha or ahora()).weekday() >= 5  # 5 es sábado y 6 es domingo.


def es_dia_especial(fecha=None):  # Indica si hay fin de semana o feriado.
    return es_fin_de_semana(fecha) or bool(feriado_de(fecha))  # True si se cumple alguna condición.


def saludo_por_hora(fecha=None):  # Devuelve un saludo según el momento del día.
    hora = (fecha or ahora()).hour  # Toma la hora de la fecha indicada o de hoy.
    if 6 <= hora < 12:  # Mañana.
        return "Buenos días"  # Saludo de mañana.
    if 12 <= hora < 20:  # Tarde.
        return "Buenas tardes"  # Saludo de tarde.
    return "Buenas noches"  # Saludo de noche.


def texto_dia_actual():  # Explica si hoy es feriado, fin de semana o día normal.
    fecha = ahora()  # Toma la fecha actual.
    feriado = feriado_de(fecha)  # Consulta si hoy es feriado.
    if feriado:  # Si hoy es feriado...
        return f"Hoy es {nombre_dia(fecha)}, feriado ({feriado}). Horarios reducidos como fin de semana."
    if es_fin_de_semana(fecha):  # Si hoy es fin de semana...
        return f"Hoy es {nombre_dia(fecha)}, fin de semana. Horarios reducidos."
    return f"Hoy es {nombre_dia(fecha)}, día de semana. Horarios normales."  # Día normal.


def tipo_de_dia(f):  # Detecta si el usuario pidió horarios de semana o de fin de semana/feriado.
    if contiene(f, ("fin de semana", "finde", "sabado", "domingo", "feriado")):  # Palabras de fin de semana.
        return "finde"  # Clave de horario reducido.
    if contiene(f, ("dia de semana", "dias de semana", "entre semana", "lunes a viernes")):  # Palabras de semana.
        return "semana"  # Clave de horario normal.
    return None  # Si no especifica, se manejará automáticamente.


def usa_horario_reducido(tipo=None):  # Determina si corresponde usar horarios de fin de semana.
    return es_dia_especial() if tipo is None else tipo == "finde"  # Auto usa hoy; "finde" fuerza reducido.


def horarios_zona(zona, tipo=None):  # Devuelve el diccionario de horarios de una zona según el tipo de día.
    if usa_horario_reducido(tipo):  # Si corresponde horario reducido...
        return HORARIOS_FINDE[zona]  # Devuelve los horarios de fin de semana.
    return ZONAS[zona]["horarios"]  # Devuelve los horarios normales.


def zona_de(destino):  # Indica a qué zona pertenece un destino.
    for clave, zona in ZONAS.items():  # Recorre sur y norte.
        if destino in zona["destinos"]:  # Si el destino está en la zona...
            return clave  # Devuelve "sur" o "norte".
    return "sur"  # Valor por defecto si no se encuentra.


def horarios_destino(destino, tipo=None):  # Devuelve los horarios de un destino específico.
    return horarios_zona(zona_de(destino), tipo)  # Busca la zona y aplica el tipo de día.


def salidas_ordenadas(horarios):  # Devuelve salidas ordenadas por hora: minutos, texto y empresa.
    return sorted((a_min(hora), hora, empresa) for empresa, horas in horarios.items() for hora in horas)


def encabezado_dia(tipo=None):  # Genera el encabezado según el tipo de día solicitado.
    if tipo == "finde":  # Si pidió fin de semana...
        return "Horarios de fin de semana y feriados."  # Encabezado de horario reducido.
    if tipo == "semana":  # Si pidió día de semana...
        return "Horarios de días de semana."  # Encabezado de horario normal.
    return texto_dia_actual()  # Si no especificó, describe el día actual.


def detectar_destino(frase):  # Busca un destino conocido dentro de la frase del usuario.
    f = normalizar(frase)  # Normaliza acentos y signos para facilitar la búsqueda.
    for zona in ZONAS.values():  # Recorre todas las zonas.
        for destino in zona["destinos"]:  # Recorre los destinos de la zona.
            if normalizar(destino) in f:  # Si el destino aparece en la frase...
                return destino  # Devuelve el destino encontrado.
    for alias, destino in ALIAS_DESTINOS.items():  # Si no aparece el nombre completo, busca alias.
        if alias in f:  # Si el alias aparece en la frase...
            return destino  # Devuelve el destino asociado al alias.
    return None  # No se reconoció ningún destino.


def detectar_empresa(frase):  # Busca una empresa mencionada en la frase.
    f = normalizar(frase)  # Normaliza la frase.
    for empresa in CONTACTOS:  # Recorre las empresas conocidas.
        if normalizar(empresa) in f:  # Si aparece el nombre de la empresa...
            return empresa  # Devuelve la empresa encontrada.
    return "Quiaqueño" if "quiaque" in f else None  # Reconoce la forma abreviada "quiaque".


def txt_menu():  # Devuelve el menú de consultas disponibles.
    return ("Consultas disponibles:\n"
            "• Horarios y próximos colectivos\n"
            "• Precios, forma de pago y duración del viaje\n"
            "• Comparación de empresas\n"
            "• Envíos y encomiendas\n"
            "• Terminal y boletería\n"
            "• Contactos de las empresas\n\n"
            "Seleccione una opción o indique su destino.")


def txt_contactos():  # Arma la lista de contactos de todas las empresas.
    lineas = ["Contactos de las empresas:"]  # Inicializa el texto con un título.
    lineas.extend(f"• {empresa}: {telefono}" for empresa, telefono in CONTACTOS.items())  # Agrega cada teléfono.
    return "\n".join(lineas)  # Une las líneas con saltos de línea.


def txt_envios():  # Explica qué empresas hacen envíos y cómo consultar condiciones.
    lineas = ["Empresas que realizan envíos y encomiendas:"]  # Inicializa el texto.
    lineas.extend(f"• {empresa}: {CONTACTOS[empresa]}" for empresa in EMPRESAS_ENVIOS)  # Agrega contactos.
    lineas.extend(["", "Para enviar un paquete, consulte en la terminal el procedimiento y las condiciones.",
                   "Para retirar una encomienda, verifique con la empresa."])  # Agrega advertencias.
    return "\n".join(lineas)  # Devuelve el texto completo.


def txt_terminal():  # Devuelve información sobre la terminal, boletería y encomiendas.
    return ("Los servicios de salida funcionan desde la Terminal de Abra Pampa.\n"
            f"• Boletería: {HORARIO_BOLETERIA}.\n"
            "• Compra de pasajes: en boletería.\n"
            f"• Encomiendas: {con_y(EMPRESAS_ENVIOS)}.")


def txt_todos_horarios(tipo=None):  # Muestra todos los horarios disponibles por zona y empresa.
    lineas = [encabezado_dia(tipo), "Estos son todos los horarios desde Abra Pampa:"]  # Encabezado general.
    for clave, zona in ZONAS.items():  # Recorre cada zona.
        lineas.append(f"\n{zona['titulo']} - {con_y(zona['destinos'])}:")  # Muestra título y destinos.
        for empresa, horas in horarios_zona(clave, tipo).items():  # Recorre empresas de la zona.
            lineas.append(f"  • {empresa}: {' - '.join(horas)} hs")  # Muestra los horarios de la empresa.
    if usa_horario_reducido(tipo):  # Si el horario es reducido...
        lineas.append(f"\n{MSG_NOTA_REDUCIDO}")  # Agrega la nota de advertencia.
    return "\n".join(lineas)  # Devuelve el texto final.


def txt_horarios(destino, tipo=None):  # Muestra horarios, duración y precio para un destino.
    duracion = DURACION_MIN.get(destino, 60)  # Obtiene la duración; usa 60 minutos por defecto.
    lineas = [encabezado_dia(tipo), f"Salidas desde Abra Pampa hacia {destino}:",
              f"Duración estimada: {formatear_duracion(duracion)}."]  # Arma el encabezado.
    lineas.extend(f"• {empresa}: {' - '.join(horarios)} hs"
                  for empresa, horarios in horarios_destino(destino, tipo).items())  # Agrega cada empresa.
    lineas.append(f"Precio del boleto: {PRECIOS[destino]} (igual en todas las empresas).")  # Muestra el precio.
    if usa_horario_reducido(tipo):  # Si corresponde...
        lineas.append(MSG_NOTA_REDUCIDO)  # Agrega la nota de horario reducido.
    return "\n".join(lineas)  # Devuelve el texto final.


def txt_todos_proximos():  # Muestra los próximos colectivos de todas las zonas.
    fecha = ahora()  # Toma la hora actual.
    minutos = fecha.hour * 60 + fecha.minute  # Convierte la hora actual a minutos.
    lineas = [texto_dia_actual(),
              f"Son las {fecha.strftime('%H:%M')}. Estos son los próximos colectivos desde Abra Pampa:"]
    for clave, zona in ZONAS.items():  # Recorre las zonas.
        lineas.append(f"\n{zona['titulo']} - {con_y(zona['destinos'])}:")  # Muestra el encabezado de la zona.
        salidas = salidas_ordenadas(horarios_zona(clave))  # Obtiene salidas ordenadas.
        restantes = [s for s in salidas if s[0] >= minutos]  # Filtra salidas que todavía no pasaron.
        if restantes:  # Si quedan salidas hoy...
            for _, hora, empresa in restantes[:4]:  # Muestra hasta cuatro salidas.
                marca = "  • ÚLTIMO DE HOY" if hora == salidas[-1][1] else ""  # Marca la última salida.
                lineas.append(f"  • {hora} hs: {empresa}{marca}")  # Agrega la salida al texto.
        else:  # Si ya no quedan salidas hoy...
            lineas.append(f"  Ya no quedan hoy. El primero de mañana es {salidas[0][1]} hs con {salidas[0][2]}.")
    return "\n".join(lineas)  # Devuelve el texto final.


def txt_proximo(destino):  # Muestra los próximos colectivos hacia un destino y la llegada estimada.
    fecha = ahora()  # Toma la hora actual.
    minutos = fecha.hour * 60 + fecha.minute  # Convierte la hora actual a minutos.
    salidas = salidas_ordenadas(horarios_destino(destino))  # Obtiene salidas ordenadas del destino.
    restantes = [s for s in salidas if s[0] >= minutos]  # Filtra las salidas futuras.
    encabezado = f"{texto_dia_actual()} Son las {fecha.strftime('%H:%M')}. "  # Arma el encabezado.
    if not restantes:  # Si no quedan salidas hoy...
        return encabezado + (f"Ya no quedan hoy a {destino}. "
                             f"El primero de mañana es {salidas[0][1]} hs con {salidas[0][2]}.")
    duracion = DURACION_MIN.get(destino, 60)  # Obtiene la duración estimada.
    lineas = [encabezado + f"El próximo a {destino} es: (viaje de {formatear_duracion(duracion)} aprox)"]
    for _, hora, empresa in restantes[:3]:  # Muestra hasta tres salidas.
        marca = "  • Es el último de hoy." if hora == salidas[-1][1] else ""  # Marca la última salida.
        lineas.append(f"  • {hora} hs: {empresa} -> llega aprox {sumar_minutos(hora, duracion)} hs.{marca}")
    _, hora, empresa = restantes[0]  # Toma la primera salida como recomendada.
    lineas.append(f"\nEl servicio recomendado es el de {hora} hs con {empresa}, llega {sumar_minutos(hora, duracion)} hs.")
    return "\n".join(lineas)  # Devuelve el texto final.


def txt_todos_precios():  # Muestra precios y duración de todos los destinos.
    lineas = ["Precios de los pasajes desde Abra Pampa:",
              "El valor depende del destino; para un mismo destino, todas las empresas cobran lo mismo.",
              "Los boletos se compran en boletería."]  # Texto inicial.
    for zona in ZONAS.values():  # Recorre las zonas.
        lineas.append(f"\n{zona['titulo']}:")  # Muestra el título de la zona.
        lineas.extend(f"• {destino}: {PRECIOS[destino]} — viaje estimado: "
                      f"{formatear_duracion(DURACION_MIN[destino])}"
                      for destino in zona["destinos"])  # Agrega precio y duración de cada destino.
    return "\n".join(lineas)  # Devuelve el texto final.


def txt_precio(destino):  # Devuelve precio, duración y forma de pago de un destino.
    return (f"Pasaje a {destino}: {PRECIOS[destino]}.\n"
            f"Duración estimada del viaje: {formatear_duracion(DURACION_MIN[destino])}.\n"
            "El precio es el mismo en todas las empresas y se abona en boletería.")


def txt_precio_multiple(destino, cantidad):  # Calcula el total de varios boletos.
    if not destino:  # Si no se indicó destino...
        return "¿Para qué destino necesita calcular el total?"  # Pide el destino.
    if cantidad == 1:  # Si es un solo boleto...
        return txt_precio(destino)  # Muestra el precio simple.
    precio_unitario = precio_a_numero(PRECIOS[destino])  # Convierte el precio a número.
    total = formatear_precio(precio_unitario * cantidad)  # Multiplica por la cantidad y da formato.
    return (f"Total por {cantidad} boletos a {destino}: {total}.\n"
            f"Precio por boleto: {PRECIOS[destino]}.\n"
            "El valor es igual en todas las empresas. Se abona en boletería.")


def txt_duracion(destino):  # Devuelve la duración estimada y el precio de un destino.
    return (f"Duración estimada hasta {destino}: {formatear_duracion(DURACION_MIN[destino])}.\n"
            f"Precio del pasaje: {PRECIOS[destino]}.")


def txt_mas_economica(destino=None):  # Explica que el precio no varía entre empresas para un mismo destino.
    if destino:  # Si el usuario indicó destino...
        return (f"Para {destino}, el pasaje cuesta {PRECIOS[destino]} en todas las empresas.\n"
                "No hay una empresa más económica para ese destino; puede elegir según el horario.")
    return ("Para un mismo destino, todas las empresas cobran lo mismo. "
            "El precio varía según la distancia.\n"
            f"Ejemplos: Humahuaca {PRECIOS['Humahuaca']} y Tilcara {PRECIOS['Tilcara']}.\n"
            "Indique su destino para mostrarle el precio y los horarios.")


def txt_comparar(destino):  # Compara la cantidad de salidas de las empresas hacia un destino.
    if not destino:  # Si no hay destino...
        return MSG_PEDIR_DESTINO_COMPARAR  # Pide el destino.
    horarios = horarios_destino(destino)  # Obtiene los horarios del destino.
    lineas = [f"Comparación de servicios hacia {destino}:",
              f"Pasaje: {PRECIOS[destino]} en todas las empresas.",
              f"Duración estimada: {formatear_duracion(DURACION_MIN[destino])}.", ""]  # Encabezado.
    for empresa, salidas in horarios.items():  # Recorre cada empresa.
        lineas.append(f"• {empresa}: {len(salidas)} salidas; primera {salidas[0]} hs; "
                      f"última {salidas[-1]} hs.")  # Muestra frecuencia y extremos.
    empresa_max, salidas_max = max(horarios.items(), key=lambda item: len(item[1]))  # Empresa con más salidas.
    lineas.extend(["", f"Mayor frecuencia: {empresa_max} ({len(salidas_max)} salidas).",
                   "Como el precio es igual, la elección puede basarse en el horario."])  # Conclusión.
    return "\n".join(lineas)  # Devuelve el texto final.


def txt_para_que_sirve_comparar():  # Explica para qué sirve comparar empresas.
    return ("La comparación permite revisar la frecuencia y los horarios de cada empresa.\n"
            "El precio para un mismo destino es igual en todas.\n"
            "Puede consultar, por ejemplo: «Comparar empresas a Tilcara».")


def txt_feriado_o_finde():  # Explica si hay servicio en feriados y fines de semana.
    fecha = ahora()  # Toma la fecha actual.
    feriado = feriado_de(fecha)  # Consulta si hoy es feriado.
    if feriado:  # Si hoy es feriado...
        return (f"Sí. Hoy es feriado ({feriado}). Hay servicio, pero con horarios reducidos, como fin de semana.\n\n"
                + txt_todos_horarios(tipo="finde"))  # Muestra horarios reducidos.
    if es_fin_de_semana(fecha):  # Si hoy es fin de semana...
        return (f"Sí. Hoy es {nombre_dia(fecha)}. Hay servicio, pero con horarios reducidos.\n\n"
                + txt_todos_horarios(tipo="finde"))  # Muestra horarios reducidos.
    return ("Sí. Los fines de semana hay servicio, pero con horarios reducidos.\n"
            "Los horarios no son los mismos que los días de semana; hay menos salidas.\n"
            "Los feriados también utilizan el horario de fin de semana.\n\n"
            + txt_todos_horarios(tipo="finde"))  # Respuesta general con horarios reducidos.


def txt_requisitos():  # Indica qué se necesita para viajar.
    return ("Para viajar, la persona debe llevar:\n"
            "• Documento Nacional de Identidad (DNI). Se acepta en formato físico o digital desde Mi Argentina.\n"
            "• Boleto comprado en la boletería de la terminal.\n"
            "• Si viaja una persona menor de edad, consulte previamente con la empresa "
            "los requisitos y autorizaciones aplicables.\n"
            "Se recomienda llegar con anticipación.")


def txt_documento_digital():  # Explica que se puede viajar con DNI digital.
    return ("Sí. Se puede viajar con el Documento Nacional de Identidad (DNI) digital.\n"
            "Puede presentarlo desde la aplicación Mi Argentina.\n"
            "Es válido como documento de identidad para viajar.\n"
            "Recuerde llevar también el boleto comprado en la boletería de la terminal.")


def txt_forma_pago():  # Explica los medios de pago y dónde se emite el boleto.
    return ("Forma de pago del boleto:\n"
            "• Se puede pagar en efectivo.\n"
            "• Se puede pagar por transferencia.\n\n"
            "Para completar el pago, debe acercarse a la boletería de la Terminal de Abra Pampa, "
            f"donde se emite el boleto. Boletería: {HORARIO_BOLETERIA}.")


def txt_mascotas():  # Indica que no hay información confirmada sobre viajar con mascotas.
    return ("Con respecto a viajar con mascotas, no se cuenta con información confirmada.\n"
            "Cada empresa establece sus propios requisitos y condiciones.\n"
            "Por ese motivo, se recomienda consultar directamente con la empresa "
            "con la que desea viajar, antes de presentarse en la terminal.\n\n"
            + txt_contactos())  # Agrega contactos para consultar.


def txt_preguntas_frecuentes():  # Devuelve un resumen de las consultas más comunes.
    return ("Consultas frecuentes:\n"
            "• ¿Hay colectivos los fines de semana y feriados? Sí, con horarios reducidos.\n"
            f"• ¿Dónde se toma el colectivo? En la Terminal de Abra Pampa.\n"
            f"• ¿Dónde se compra el boleto? En boletería, {HORARIO_BOLETERIA}.\n"
            "• ¿Cómo se puede pagar? En efectivo o por transferencia, en la terminal.\n"
            f"• ¿Cuál es la duración del viaje a Humahuaca? Aproximadamente {formatear_duracion(DURACION_MIN['Humahuaca'])}.\n"
            f"• ¿Qué empresas realizan envíos? {con_y(EMPRESAS_ENVIOS)}.\n"
            "• ¿Qué debe llevar para viajar? Documento Nacional de Identidad (DNI) y boleto.\n"
            "• ¿Se puede viajar con DNI digital? Sí, desde Mi Argentina.\n"
            "• ¿Se puede viajar con mascotas? No se cuenta con información confirmada; consulte con la empresa.")


def txt_bienvenida():  # Genera el mensaje de bienvenida del chatbot.
    return (f"{saludo_por_hora()}. Soy el asistente virtual de colectivos de Abra Pampa.\n\n"
            "Puedo ayudarle con horarios, próximos servicios, precios, forma de pago, duración del viaje, "
            "comparación de empresas, envíos y datos de la terminal.\n\n"
            f"Hacia el sur: {con_y(ZONAS['sur']['destinos'])}.\n"
            f"Hacia el norte: {con_y(ZONAS['norte']['destinos'])}.\n\n"
            "Seleccione una opción de los botones o escriba su consulta.")


# FRASES contiene ejemplos de texto para entrenar cada intención del modelo.
FRASES = {
    'saludo': ['hola', 'buenas', 'buen dia', 'buenas tardes', 'buenas noches', 'hola que tal'],  # Ejemplos de saludo.
    'despedida': ['chau', 'chao', 'adios', 'hasta luego', 'nos vemos', 'me voy', 'eso es todo gracias'],  # Ejemplos de despedida.
    'gracias': ['gracias', 'muchas gracias'],  # Ejemplos de agradecimiento.
    'ayuda': ['que informacion me puede brindar', 'que informacion me puedes brindar', 'que sabe hacer',
              'que puede hacer', 'menu', 'ayuda', 'inicio', 'preguntas frecuentes'],  # Ejemplos de ayuda.
    'horarios_todos': [
        'horarios', 'todos los horarios', 'ver horarios', 'quiero todos los horarios',
        'horarios para humahuaca', 'horarios para leon', 'horarios para tilcara',
        'horarios para tres cruces', 'quiero saber los horarios a tres cruces', 'y a leon', 'y a tilcara',
        'y a humahuaca', 'que colectivos salen para jujuy', 'que colectivos salen para humahuaca',
        'que colectivos salen de abra pampa', 'horarios desde abra pampa', 'y los horarios',
        'a que hora sale el colectivo a jujuy', 'a que hora sale', 'que colectivos hay',
        'horarios de fin de semana', 'horarios del sabado', 'horarios del domingo',
        'cuales son los horarios del fin de semana', 'horarios del finde',
        'cuales son los horarios del finde'],  # Ejemplos de consulta de horarios.
    'proximo': [
        'que colectivos salen ahora', 'proximo colectivo a tilcara', 'cual es el proximo',
        'que sale ahora', 'y el proximo', 'proximo colectivo', 'proximos colectivos',
        'todos los proximos', 'quiero saber que colectivo sale ahora', 'que colectivo sale ahora',
        'cual es el proximo colectivo a tres cruces', 'cual es el proximo colectivo',
        'que colectivo sale ahora para jujuy', 'que colectivo sale ahora para la quiaca',
        'cual es el proximo horario para la quiaca', 'cual es el proximo horario para jujuy',
        'proximo horario para la quiaca', 'que colectivo sale ahora para humahuaca'],  # Ejemplos de próximas salidas.
    'precio_boleto': [
        'cuanto sale el boleto a humahuaca', 'precio a tilcara', 'cuanto cuesta viajar a leon',
        'y cuanto', 'y cuanto sale', 'y cuanto esta', 'cuanto esta', 'precios', 'todos los precios',
        'precio de los boletos', 'cuales son los precios', 'y cuales son los precios',
        'y los precios', 'cuanto sale el pasaje a la quiaca', 'cuanto sale ir a la quiaca',
        'cuanto sale el boleto', 'cuanto sale ir a tilcara'],  # Ejemplos de consulta de precios.
    'precio_multiple': [
        'cuanto sale tres boletos para tilcara', 'cuanto salen dos boletos para jujuy',
        'cuanto sale 2 boletos', 'precio de 3 boletos', 'cuanto sale para 3 personas',
        'cuanto salen 3 boletos para tilcara', 'cuanto sale dos boletos para humahuaca',
        'cuanto sale tres boletos', 'somos tres cuanto sale', 'somos 2 cuanto sale',
        'cuanto sale para 3 personas a tilcara'],  # Ejemplos de cálculo de varios boletos.
    'mas_economica': [
        'cual es la mas barata', 'cual es la mas economica', 'cual es mas barato',
        'que empresa es mas barata', 'que empresa es mas economica', 'cual sale mas barato',
        'cual cobra menos', 'cual es la empresa mas economica', 'cual es la empresa mas barata',
        'busco lo mas barato', 'quiero lo mas economico', 'cual me conviene por precio',
        'hay alguna mas barata', 'la mas barata a humahuaca', 'la mas economica a tilcara'],  # Ejemplos de búsqueda de precio bajo.
    'comparar': ['comparar empresas', 'comparar', 'cual tiene mas salidas',
                 'cual empresa tiene mas salidas', 'que empresa sale mas seguido', 'comparar las empresas'],  # Ejemplos de comparación.
    'para_que_comparar': ['para que sirve comparar', 'para que sirve comparar empresas',
                          'que es comparar', 'por que comparar', 'para que comparar',
                          'que significa comparar'],  # Ejemplos de consulta sobre comparar.
    'duracion': [
        'cuanto tarda', 'cuanto dura el viaje', 'cuanto tiempo tarda', 'cuanto tarda el colectivo',
        'a que hora llego', 'cuanto demora', 'cuanto tarda en llegar hasta leon',
        'cuanto tarda en llegar a leon', 'cuanto tarda hasta tilcara', 'cuanto tarda en llegar',
        'cuanto tarda', 'cuanto tarda en llegar hasta humahuaca',
        'cuanto tarda en llegar hasta leon', 'cuanto tarda a humahuaca',
        'cuanto tarda el viaje a humahuaca', 'cual es la duracion del viaje',
        'duracion del viaje', 'cuanto dura', 'cual es la duracion'],  # Ejemplos de duración del viaje.
    'feriado_finde': [
        'hay colectivo el domingo', 'hay colectivos el domingo', 'hay colectivo el sabado',
        'hay colectivos el sabado', 'hay colectivo el fin de semana', 'hay colectivo el feriado',
        'hay colectivos el feriado', 'mañana es feriado hay colectivo', 'hoy es feriado',
        'funcionan el feriado', 'hay servicio el domingo',
        'los fines de semana los horarios son normales', 'los finde hay horarios normales',
        'los horarios del finde son normales', 'el finde hay horarios normales',
        'hay colectivo los fines de semana', 'hay colectivos los fines de semana',
        'hay servicio los fines de semana'],  # Ejemplos de feriados y fines de semana.
    'terminal': [
        'donde tomo el colectivo', 'donde sale el colectivo', 'donde esta la terminal',
        'donde queda la terminal', 'horario de boleteria', 'a que hora abre la boleteria',
        'a que hora cierra la boleteria', 'donde compro el boleto', 'donde se compra el boleto',
        'donde saco el boleto', 'donde venden el boleto', 'donde puedo comprar el boleto',
        'donde puedo comprar el pasaje'],  # Ejemplos de consultas sobre la terminal.
    'encomienda': [
        'para hacer encomienda', 'como hago un envio', 'que empresa hacen envios',
        'que empresa hace envios', 'quien hace envios', 'hacen envios', 'envios a jujuy',
        'envios a humahuaca', 'hacer envios a jujuy', 'hacer envios a humahuaca',
        'quiero hacer un envio a tilcara', 'como hago envios a jujuy',
        'se puede hacer envios a jujuy', 'mandar un paquete a jujuy',
        'quiero mandar un paquete a jujuy', 'quiero retirar encomienda', 'retirar encomienda',
        'donde retiro mi encomienda', 'me llego una encomienda', 'que empresas hacen envios',
        'como hago para hacer envios', 'como hago para retirar encomiendas',
        'como retiro una encomienda', 'los colectivos hacen envios',
        'contactos de los que hacen envios', 'contactos de envios', 'quienes hacen envios',
        'empresas de envios', 'que empresas realizan envios', 'envios encomiendas'],  # Ejemplos de envíos.
    'contacto': [
        'telefono de balut', 'numero de contacto', 'contacto de balut', 'telefono de evelia',
        'telefono de jama', 'telefono de panamericano', 'telefono de quiaqueño', 'contactos',
        'contactos de las empresas', 'contactos empresas', 'numeros', 'telefonos', 'contacto'],  # Ejemplos de contacto.
    'requisitos': [
        'que debo tener para viajar', 'que necesito para viajar', 'que tengo que llevar para viajar',
        'que documentos necesito', 'necesito documento nacional de identidad para viajar',
        'que piden para viajar', 'que hay que llevar para viajar', 'que se necesita para viajar',
        'que documentos tengo que llevar', 'que debe llevar la persona para viajar',
        'que debe llevar para viajar', 'documento nacional de identidad para viajar',
        'documento de identidad para viajar'],  # Ejemplos de requisitos para viajar.
    'documento_digital': [
        'puedo viajar con dni digital', 'puedo viajar con documento digital',
        'se puede viajar con dni digital', 'se puede viajar con documento digital',
        'puedo viajar con mi argentina', 'se puede viajar con mi argentina',
        'puedo mostrar mi argentina', 'aceptan dni digital', 'aceptan mi argentina',
        'sirve el dni digital', 'sirve mi argentina', 'viajar con dni del celular', 'dni en el celular'],  # Ejemplos de DNI digital.
    'mascotas': [
        'se puede viajar con mascotas', 'se puede viajar con animales', 'puedo llevar a mi perro',
        'puedo viajar con mi perro', 'puedo llevar mascota', 'viajar con animales',
        'se puede llevar perro en el colectivo', 'se puede viajar con perro', 'puedo llevar a mi gato',
        'los perros pueden viajar', 'se puede llevar mascotas', 'se permite viajar con mascotas',
        'puedo viajar con mi mascota'],  # Ejemplos de consultas sobre mascotas.
    'forma_pago': [
        'como puedo pagar el boleto', 'como se puede pagar', 'como pago',
        'se puede pagar con transferencia', 'se puede pagar en efectivo', 'forma de pago',
        'como pago el boleto', 'como pago el pasaje', 'medios de pago', 'aceptan transferencia',
        'aceptan efectivo', 'se paga con transferencia', 'puedo pagar con transferencia',
        'puedo pagar en efectivo', 'con que puedo pagar'],  # Ejemplos de forma de pago.
    'otro_tema': ['el clima de hoy', 'quiero pizza', 'que hora es', 'hoy llueve', 'como te llamas',
                  'cuanto es dos mas dos', 'quien gano el partido', 'pone musica', 'contame un chiste',
                  'quiero comer', 'que dia es hoy', 'como estas', 'que tal'],  # Ejemplos fuera del dominio.
}

# textos reúne todas las frases de entrenamiento del diccionario FRASES.
textos = [frase for frases in FRASES.values() for frase in frases]
# etiquetas guarda la intención correspondiente a cada frase de entrenamiento.
etiquetas = [intencion for intencion, frases in FRASES.items() for _ in frases]

# TfidfVectorizer convierte las frases en vectores numéricos según la importancia de las palabras.
vectorizador = TfidfVectorizer(lowercase=True, strip_accents="unicode")
# LogisticRegression es el clasificador que aprende a asociar frases con intenciones.
modelo = LogisticRegression(max_iter=1000, C=20)
# fit entrena el modelo con los vectores de texto y sus etiquetas.
modelo.fit(vectorizador.fit_transform(textos), etiquetas)
# CONFIANZA_MINIMA evita responder con una predicción poco segura.
CONFIANZA_MINIMA = 0.45


def predecir_con_confianza(frase):  # Predice la intención de una frase si supera la confianza mínima.
    probabilidades = modelo.predict_proba(vectorizador.transform([frase]))[0]  # Calcula probabilidades.
    mejor = probabilidades.argmax()  # Toma la intención con mayor probabilidad.
    if probabilidades[mejor] < CONFIANZA_MINIMA:  # Si la confianza es baja...
        return "no_entendido"  # Devuelve una intención de no entendido.
    return modelo.classes_[mejor]  # Devuelve el nombre de la intención predicha.


def intencion_por_palabras(f):  # Detecta intenciones mediante reglas tolerantes de palabras clave.
    if contiene_tolerante(f, ("digital", "mi argentina", "argentina")):  # Palabras de DNI digital.
        return "documento_digital"  # Intención de documento digital.
    if contiene_tolerante(f, ("dni",)):  # Menciona DNI.
        return "documento_digital"  # Intención de documento digital.
    if contiene_tolerante(f, ("mascota", "perro", "gato", "animal")):  # Palabras de mascotas.
        return "mascotas"  # Intención de mascotas.
    if contiene_tolerante(f, ("para que sirve comparar", "para que comparar", "que es comparar")):  # Consulta meta.
        return "para_que_comparar"  # Intención de explicación de comparar.
    if contiene_tolerante(f, ("que debo tener", "que necesito para viajar", "que tengo que llevar",
                              "que piden para viajar", "que se necesita para viajar", "que debe llevar",
                              "documento nacional de identidad", "documento de identidad")):  # Requisitos.
        return "requisitos"  # Intención de requisitos.
    if contiene_tolerante(f, ("transferencia", "efectivo", "forma de pago", "como pago",
                              "como puedo pagar", "medios de pago", "aceptan")):  # Formas de pago.
        return "forma_pago"  # Intención de forma de pago.
    if contiene_tolerante(f, ("envio", "encomienda", "mandar", "paquete")):  # Envíos.
        return "encomienda"  # Intención de encomiendas.
    if contiene_tolerante(f, ("boleto", "boletos")) and contiene_tolerante(
            f, ("dos", "tres", "cuatro", "cinco", "2", "3", "4", "5")):  # Varios boletos.
        return "precio_multiple"  # Intención de precio multiple.
    if contiene_tolerante(f, ("cuanto tarde", "cuanto tardo")):  # Dudas con "tarde/tardo".
        return "duracion"  # Intención de duración.
    if contiene_tolerante(f, ("duracion", "cuanto dura")):  # Duración.
        return "duracion"  # Intención de duración.
    if contiene_tolerante(f, ("finde", "fin de semana")) and contiene_tolerante(f, ("normal", "son normales")):  # Fin de semana normal.
        return "feriado_finde"  # Intención de feriado o fin de semana.
    if re.search(r"\b(proxim[oa]s?|poxim[oa]s?)\b", f) or contiene_tolerante(
            f, ("que sale ahora", "cual sale", "cuando sale")):  # Próximas salidas.
        return "proximo"  # Intención de próximo colectivo.
    if contiene_tolerante(f, ("comparar", "comparame", "mas salidas", "sale mas seguido")):  # Comparación.
        return "comparar"  # Intención de comparar.
    if contiene_tolerante(f, ("terminal", "boleteria", "donde tomo", "donde sale", "donde compro",
                              "donde saco", "donde venden", "donde puedo comprar")):  # Terminal.
        return "terminal"  # Intención de terminal.
    if contiene_tolerante(f, ("mas barata", "mas barato", "mas economica", "mas economico",
                              "cobra menos", "lo mas barato")):  # Empresa más económica.
        return "mas_economica"  # Intención de empresa más económica.
    if contiene_tolerante(f, ("cuanto tarda", "cuanto dura", "cuanto demora", "a que hora llego",
                              "cuanto tiempo")):  # Duración del viaje.
        return "duracion"  # Intención de duración.
    if contiene_tolerante(f, ("hay colectivo", "hay servicio", "funcionan el", "hoy es feriado")) and contiene_tolerante(
            f, ("domingo", "sabado", "fin de semana", "feriado", "finde")):  # Servicio en finde.
        return "feriado_finde"  # Intención de feriado o fin de semana.
    if contiene_tolerante(f, ("contacto", "telefono", "numero de", "celular de", "contactos")):  # Contactos.
        return "contacto"  # Intención de contacto.
    if contiene_tolerante(f, ("horario", "hora sale", "a que hora", "fin de semana", "finde",
                              "sabado", "domingo")):  # Horarios.
        return "horarios_todos"  # Intención de horarios.
    if contiene_tolerante(f, ("cuanto sale", "cuanto esta", "precio", "cuanto cuesta", "cuanto vale",
                              "boleto", "pasaje")):  # Precios.
        return "precio_boleto"  # Intención de precio de boleto.
    return None  # Ninguna regla coincidió.


@dataclass  # Crea automáticamente una clase simple con inicializador y representación.
class Respuesta:  # Representa una respuesta del chatbot.
    texto: str  # Contenido textual de la respuesta.


# DESPEDIDA reconoce frases con las que el usuario indica que quiere terminar.
DESPEDIDA = re.compile(
    r"(?:no+|que no+|nada|nada mas|chau|chao|adios|hasta luego|nos vemos|salir|terminar|cerrar|"
    r"ya esta|listo|eso (?:era|es) todo|no necesito(?: nada)?(?: mas)?|no quiero nada(?: mas)?)(?: gracias)?|"
    r"no gracias|me voy")
# CONFIRMACIONES contiene respuestas afirmativas simples.
CONFIRMACIONES = {"si", "claro", "por supuesto", "si quiero"}
# INTENCIONES_CON_DESTINO son las intenciones que necesitan un destino para responder.
INTENCIONES_CON_DESTINO = ("horarios_todos", "proximo", "precio_boleto", "precio_multiple",
                           "duracion", "mas_economica", "comparar")


class Chatbot:  # Clase principal que gestiona la conversación y el contexto del usuario.
    def __init__(self):  # Inicializa el estado del chatbot.
        self.ultimo_destino = None  # Guarda el último destino mencionado.
        self.ultima_intencion = None  # Guarda la última intención detectada.
        self.ultima_cantidad = 1  # Guarda la última cantidad de boletos detectada.

    def procesar(self, frase):  # Procesa una frase del usuario y devuelve una Respuesta.
        f = normalizar(frase)  # Normaliza la frase para analizarla.
        if not f:  # Si la frase está vacía...
            return None  # No devuelve respuesta.
        if DESPEDIDA.fullmatch(f):  # Si el usuario se despide...
            self.ultimo_destino = self.ultima_intencion = None  # Limpia el contexto.
            self.ultima_cantidad = 1  # Restablece la cantidad por defecto.
            return Respuesta(MSG_DESPEDIDA)  # Devuelve el mensaje de despedida.
        if f in CONFIRMACIONES:  # Si el usuario confirma...
            return Respuesta("Perfecto. ¿Qué información necesita?\n" + txt_menu())  # Muestra el menú.
        if f in ("hora", "horar", "horari", "horario", "horarios"):  # Si pide horarios de forma breve...
            self.ultima_intencion = "horarios_todos"  # Guarda la intención.
            return Respuesta(txt_todos_horarios())  # Muestra todos los horarios.
        if f in ("contacto", "contactos", "contactos de las empresas", "numeros", "telefonos",
                 "contactos empresas"):  # Si pide contactos...
            return Respuesta(txt_contactos())  # Muestra la lista de contactos.

        por_palabras = intencion_por_palabras(f)  # Aplica reglas de palabras clave.
        destino_nuevo = detectar_destino(frase)  # Busca un destino en la frase original.
        cantidad_nueva = detectar_cantidad(f)  # Busca una cantidad en la frase normalizada.

        if destino_nuevo and len(f.split()) <= 4 and por_palabras is None:  # Frase breve solo con destino.
            self.ultimo_destino = destino_nuevo  # Guarda el destino como contexto.
            if self.ultima_intencion not in INTENCIONES_CON_DESTINO:  # Si no hay intención válida previa...
                self.ultima_intencion = "horarios_todos"  # Usa horarios por defecto.
            return self.responder(self.ultima_intencion, destino_nuevo, cantidad=self.ultima_cantidad)  # Responde.

        intencion = por_palabras or predecir_con_confianza(frase)  # Usa reglas o el modelo entrenado.

        if f.startswith("y ") and intencion in ("no_entendido", "otro_tema") and self.ultima_intencion:
            intencion = self.ultima_intencion  # "Y ..." mantiene la intención anterior.
        if f.startswith("y ") and destino_nuevo and self.ultima_intencion in INTENCIONES_CON_DESTINO:
            intencion = self.ultima_intencion  # "Y <destino>" mantiene la intención anterior.

        if destino_nuevo:  # Si se detectó un destino...
            self.ultimo_destino = destino_nuevo  # Lo guarda para futuras consultas.
        if cantidad_nueva:  # Si se detectó una cantidad...
            self.ultima_cantidad = cantidad_nueva  # La guarda para futuras consultas.

        destino = None if contiene(f, ("todos", "todas")) else (destino_nuevo or self.ultimo_destino)  # Elige destino.
        cantidad = cantidad_nueva or self.ultima_cantidad  # Elige cantidad.

        if intencion in INTENCIONES_CON_DESTINO:  # Si la intención necesita destino...
            self.ultima_intencion = intencion  # La guarda como contexto.
        return self.responder(intencion, destino, detectar_empresa(frase), tipo_de_dia(f), cantidad=cantidad)  # Responde.

    def responder(self, intencion, destino=None, empresa=None, tipo=None, cantidad=1):  # Genera la respuesta según intención.
        if intencion == "saludo":  # Saludo.
            return Respuesta(f"{saludo_por_hora()}. ¿Qué información necesita?\n" + txt_menu())
        if intencion == "despedida":  # Despedida.
            return Respuesta(MSG_DESPEDIDA)
        if intencion == "gracias":  # Agradecimiento.
            return Respuesta("De nada. Estoy para ayudarle con horarios, próximos colectivos, precios, "
                             "comparación de empresas, terminal, envíos y contactos.")
        if intencion == "ayuda":  # Ayuda.
            return Respuesta(txt_preguntas_frecuentes() + "\n\n" + txt_menu())
        if intencion == "terminal":  # Terminal.
            return Respuesta(txt_terminal())
        if intencion == "horarios_todos":  # Horarios.
            return Respuesta(txt_horarios(destino, tipo) if destino else txt_todos_horarios(tipo))
        if intencion == "proximo":  # Próximas salidas.
            return Respuesta(txt_proximo(destino) if destino else txt_todos_proximos())
        if intencion == "precio_boleto":  # Precio de boleto.
            return Respuesta(txt_precio(destino) if destino else txt_todos_precios())
        if intencion == "precio_multiple":  # Precio de varios boletos.
            return Respuesta(txt_precio_multiple(destino, cantidad))
        if intencion == "mas_economica":  # Empresa más económica.
            return Respuesta(txt_mas_economica(destino))
        if intencion == "comparar":  # Comparación.
            return Respuesta(txt_comparar(destino))
        if intencion == "para_que_comparar":  # Explicación de comparar.
            return Respuesta(txt_para_que_sirve_comparar())
        if intencion == "duracion":  # Duración del viaje.
            if destino:  # Si hay destino...
                return Respuesta(txt_duracion(destino))  # Muestra duración y precio.
            return Respuesta("¿A qué destino desea viajar?")  # Pide destino.
        if intencion == "feriado_finde":  # Feriado o fin de semana.
            return Respuesta(txt_feriado_o_finde())
        if intencion == "encomienda":  # Encomiendas.
            return Respuesta(txt_envios())
        if intencion == "contacto":  # Contactos.
            if empresa:  # Si se detectó una empresa...
                return Respuesta(f"El contacto de {empresa} es: {CONTACTOS[empresa]}.")  # Muestra su teléfono.
            return Respuesta(txt_contactos())  # Muestra todos los contactos.
        if intencion == "requisitos":  # Requisitos para viajar.
            return Respuesta(txt_requisitos())
        if intencion == "documento_digital":  # DNI digital.
            return Respuesta(txt_documento_digital())
        if intencion == "mascotas":  # Mascotas.
            return Respuesta(txt_mascotas())
        if intencion == "forma_pago":  # Forma de pago.
            return Respuesta(txt_forma_pago())
        return Respuesta(MSG_NO_ENTENDIDO + "\n" + txt_menu())  # Intención no reconocida.
