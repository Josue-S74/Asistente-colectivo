# Aplicación web Streamlit del asistente de colectivos de Abra Pampa.
# Versión simple: pantalla de inicio, menús desplegables, burbuja flotante e informe final.
import html  # Permite escapar texto para insertarlo de forma segura dentro de HTML.
from datetime import datetime, timedelta, timezone  # Permite calcular horas, diferencias y zona horaria.

import streamlit as st  # Streamlit crea la interfaz web y administra el estado de la sesión.

# Se importan datos y funciones del módulo NLP para no duplicar lógica en la interfaz.
from chatbot_nlp_nuevo import (
    Chatbot,  # Clase que procesa las consultas del chat.
    CONTACTOS,  # Diccionario de teléfonos por empresa.
    DURACION_MIN,  # Duración estimada de viaje por destino.
    EMPRESAS_ENVIOS,  # Empresas que realizan envíos.
    HORARIO_BOLETERIA,  # Horario de atención de la boletería.
    MSG_NOTA_REDUCIDO,  # Aviso de horarios reducidos.
    PRECIOS,  # Precios de boletos por destino.
    ZONAS,  # Destinos y horarios agrupados por zona.
    encabezado_dia,  # Genera el texto del encabezado según el tipo de día.
    es_dia_especial,  # Detecta fin de semana o feriado.
    formatear_duracion,  # Convierte minutos a texto legible.
    horarios_destino,  # Devuelve los horarios de un destino.
    sumar_minutos,  # Suma minutos a una hora para estimar llegadas.
    txt_bienvenida,  # Texto de bienvenida del chat.
    txt_comparar,  # Texto de comparación de empresas.
    txt_contactos,  # Texto con todos los contactos.
    txt_documento_digital,  # Texto sobre DNI digital.
    txt_envios,  # Texto de envíos y encomiendas.
    txt_forma_pago,  # Texto de medios de pago.
    txt_horarios,  # Texto con horarios, duración y precio de un destino.
    txt_mascotas,  # Texto sobre mascotas.
    txt_precio,  # Texto con precio y duración de un destino.
    txt_preguntas_frecuentes,  # Texto de preguntas frecuentes.
    txt_proximo,  # Texto con próximas salidas de un destino.
    txt_requisitos,  # Texto de requisitos para viajar.
    txt_terminal,  # Texto de información de la terminal.
    usa_horario_reducido,  # Indica si corresponde aplicar horario reducido.
    zona_de,  # Devuelve la zona de un destino.
)

ZONA_HORARIA = timezone(timedelta(hours=-3), "ART")  # Define la zona horaria de Argentina.

# REQUISITOS_ENCOMIENDAS enumera los pasos que el usuario confirma antes de enviar un paquete.
REQUISITOS_ENCOMIENDAS = {
    "Destinatario": ["Nombre completo, DNI y celular."],  # Datos de quien recibe.
    "Remitente": ["Nombre completo, fotocopia del DNI y celular."],  # Datos de quien envía.
    "Embalaje": [  # Condiciones del paquete.
        "1 sintex, papel madera o bolsa negra.",  # Material de embalaje permitido.
        "Una hoja A4 en blanco.",  # Hoja solicitada para la encomienda.
        "Traer la caja o bolsa abierta.",  # Indicación para la revisión.
    ],
    "Retiro": ["DNI físico o Mi Argentina, sin excepción."],  # Documento para retirar.
}

# BOTONES_FRECUENTES muestra consultas rápidas dentro del menú de chat.
BOTONES_FRECUENTES = [
    "¿Hay colectivo los fines de semana?",  # Consulta sobre servicio en fin de semana.
    "¿Qué necesito para viajar?",  # Consulta sobre requisitos.
    "¿Puedo viajar con DNI digital?",  # Consulta sobre documento digital.
    "¿Cuál es la duración del viaje?",  # Consulta sobre duración.
    "¿Qué empresas realizan envíos?",  # Consulta sobre encomiendas.
    "¿Dónde puedo comprar el boleto?",  # Consulta sobre boletería.
    "¿Se puede viajar con mascotas?",  # Consulta sobre mascotas.
    "¿Cómo puedo pagar el boleto?",  # Consulta sobre forma de pago.
]


def formatear_duracion_viva(segundos):  # Convierte segundos restantes a un contador "HH:MM:SS".
    segundos = max(0, int(segundos))  # Evita valores negativos y convierte a entero.
    horas, resto = divmod(segundos, 3600)  # Separa las horas del total de segundos.
    minutos, segundos = divmod(resto, 60)  # Separa minutos y segundos restantes.
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"  # Devuelve el contador con dos dígitos.


def construir_salidas(horarios, empresas, ahora, duracion):  # Arma la lista de próximas salidas.
    salidas = []  # Inicializa la lista de resultados.
    for empresa, horas in horarios.items():  # Recorre todas las empresas y sus horarios.
        if empresa not in empresas:  # Si la empresa no está seleccionada en el filtro...
            continue  # La ignora.
        for hora in horas:  # Recorre cada horario de la empresa.
            hora_salida, minuto_salida = (int(parte) for parte in hora.split(":"))  # Separa hora y minuto.
            fecha_salida = ahora.replace(  # Crea la fecha de salida con la hora del horario.
                hour=hora_salida,  # Asigna la hora de salida.
                minute=minuto_salida,  # Asigna el minuto de salida.
                second=0,  # Pone segundos en cero.
                microsecond=0,  # Pone microsegundos en cero.
            )
            if fecha_salida < ahora:  # Si la salida ya pasó hoy...
                fecha_salida += timedelta(days=1)  # La considera como salida de mañana.
            salidas.append({  # Guarda los datos de la salida.
                "hora": hora,  # Hora informada en el horario.
                "empresa": empresa,  # Empresa que realiza el viaje.
                "segundos": (fecha_salida - ahora).total_seconds(),  # Segundos restantes para el contador.
                "manana": fecha_salida.date() > ahora.date(),  # Indica si es salida de mañana.
                "llegada": sumar_minutos(hora, duracion),  # Hora estimada de llegada.
            })
    salidas.sort(key=lambda salida: salida["segundos"])  # Ordena por tiempo restante.
    return salidas  # Devuelve la lista ordenada.


def construir_informe_final(destino, tipo, horarios, empresas, cantidad, duracion):  # Genera el resumen del destino.
    ahora = datetime.now(ZONA_HORARIA)  # Toma la hora actual para calcular próximas salidas.
    salidas = construir_salidas(horarios, empresas, ahora, duracion)[:cantidad]  # Aplica el filtro elegido.
    lineas = [  # Inicializa el informe con los datos principales.
        "INFORME FINAL - ASISTENTE DE COLECTIVOS DE ABRA PAMPA",
        "",
        f"Destino seleccionado: {destino}",
        f"Zona: {zona_de(destino)}",
        f"Tipo de día: {encabezado_dia(tipo)}",
        "",
        "1) PRECIO Y DURACIÓN",
        txt_precio(destino),
        "",
        "2) HORARIOS",
        txt_horarios(destino, tipo),
        "",
        "3) PRÓXIMAS SALIDAS SEGÚN EL FILTRO",
    ]
    if salidas:  # Si hay salidas para el filtro...
        for salida in salidas:  # Recorre las salidas calculadas.
            marca = " (mañana)" if salida["manana"] else ""  # Marca las salidas del día siguiente.
            lineas.append(  # Agrega una línea por salida.
                f"• {salida['hora']} hs - {salida['empresa']}{marca} - llega {salida['llegada']} "
                f"- faltan {formatear_duracion_viva(salida['segundos'])}"
            )
    else:  # Si no hay salidas...
        lineas.append("No hay salidas cargadas para el filtro seleccionado.")  # Avisa en el informe.
    lineas.extend([  # Agrega el resto de secciones del informe.
        "",
        "4) COMPARACIÓN DE EMPRESAS",
        txt_comparar(destino),
        "",
        "5) ENCOMIENDAS",
        txt_envios(),
        "",
        "6) TERMINAL Y PAGOS",
        txt_terminal(),
        txt_forma_pago(),
        "",
        "7) REQUISITOS PARA VIAJAR",
        txt_requisitos(),
        "",
        "8) CONTACTOS",
        txt_contactos(),
        "",
        "Verifique horarios y precios en la terminal antes de viajar.",
    ])
    return "\n".join(lineas)  # Devuelve el informe como texto.


def guardar_informe_actual():  # Guarda la selección vigente para que el informe use ese destino.
    st.session_state.informe_destino = st.session_state["destino_actual"]  # Guarda el destino elegido.
    st.session_state.informe_tipo = st.session_state["tipo_actual"]  # Guarda el tipo de día elegido.
    st.session_state.informe_empresas = st.session_state["empresas_actuales"]  # Guarda las empresas elegidas.
    st.session_state.informe_cantidad = st.session_state["cantidad_actual"]  # Guarda la cantidad elegida.


def es_consulta_resumen(texto):  # Detecta si el usuario pidió el informe final o un resumen.
    t = texto.lower()  # Pasa el texto a minúsculas.
    return any(palabra in t for palabra in ("resumen", "informe final", "informe", "ver informe"))  # Busca claves.


def formatear_texto_chat(texto):  # Prepara el texto para que se lea con más espacio en Markdown.
    return texto.replace("\n", "  \n")  # Agrega dos espacios antes de cada salto de línea.


def mostrar_mensaje_chat(rol, texto, indice):  # Dibuja un mensaje con un recuadro según quién habla.
    prefijo = "asistente" if rol == "assistant" else "usuario"  # Define el color del recuadro.
    with st.container(key=f"mensaje_{prefijo}_{indice}"):  # Clave única para aplicar el CSS del recuadro.
        with st.chat_message(rol, width="content"):  # Muestra el avatar y la burbuja de Streamlit.
            st.markdown(formatear_texto_chat(texto))  # Renderiza el texto con saltos visibles y más altura.


def enviar_consulta(texto):  # Envía una consulta al chatbot y actualiza el historial.
    texto = texto.strip()  # Quita espacios alrededor del texto.
    if not texto:  # Si la consulta quedó vacía...
        return  # No hace nada.
    if es_consulta_resumen(texto):  # Si el usuario pidió un resumen...
        st.session_state.mensajes.append({"rol": "user", "texto": texto})  # Guarda su mensaje.
        st.session_state.mensajes.append({  # Agrega la respuesta del asistente.
            "rol": "assistant",
            "texto": "Abrí el Informe final al final de la página con el resumen del destino seleccionado.",
        })
        guardar_informe_actual()  # Toma el destino seleccionado en el panel lateral.
        st.session_state.mostrar_informe = True  # Muestra el resumen.
        st.session_state.abrir_informe = True  # Abre el menú del informe.
        st.session_state.abrir_chat = False  # Cierra la ventana del asistente.
        st.session_state.scroll_informe = True  # Desplaza la vista al informe.
        st.rerun()  # Vuelve a ejecutar la app.
    st.session_state.mensajes.append({"rol": "user", "texto": texto})  # Guarda mensaje del usuario.
    mostrar_mensaje_chat("user", texto, len(st.session_state.mensajes) - 1)  # Muestra el recuadro del usuario.
    respuesta = st.session_state.bot.procesar(texto)  # Pide la respuesta al chatbot.
    if respuesta:  # Si el chatbot devolvió una respuesta...
        st.session_state.mensajes.append({"rol": "assistant", "texto": respuesta.texto})  # La guarda.
        mostrar_mensaje_chat("assistant", respuesta.texto, len(st.session_state.mensajes) - 1)  # Muestra su recuadro.


def cerrar_chat():  # Limpia la bandera cuando se cierra la ventana del asistente.
    st.session_state.abrir_chat = False  # Permite volver a abrirla desde la burbuja.
    st.session_state.consulta_habilitada = False  # Vuelve a pedir el botón en la próxima apertura.


def habilitar_escritura():  # Habilita el campo cuando se pulsa el botón inicial.
    st.session_state.consulta_habilitada = True  # Permite escribir la consulta.
    st.session_state.foco_chat = True  # Enfoca el campo después de habilitarlo.


@st.dialog("Asistente de colectivos", width="large", dismissible=True, on_dismiss=cerrar_chat)  # Muestra el chat como ventana modal.
def ventana_chat():  # Contiene todo el chat; solo se abre desde la burbuja flotante.
    if "bot" not in st.session_state:  # Si aún no existe el chatbot en la sesión...
        st.session_state.bot = Chatbot()  # Crea una nueva instancia.
    if "mensajes" not in st.session_state:  # Si aún no hay historial...
        st.session_state.mensajes = [{"rol": "assistant", "texto": txt_bienvenida()}]  # Inicia con bienvenida.

    with st.container(key="chat_historial"):  # Contenedor con clave para aplicar CSS propio.
        for indice, mensaje in enumerate(st.session_state.mensajes):  # Recorre el historial de mensajes.
            mostrar_mensaje_chat(mensaje["rol"], mensaje["texto"], indice)  # Dibuja el recuadro según el rol.

    st.html(  # Deja visible el último mensaje cuando el historial supera la altura de la ventana.
        "<script>setTimeout(function(){const h=document.querySelector('[class*=st-key-chat_historial]');"
        "if(h){h.scrollTop=h.scrollHeight;}},150);</script>"
    )

    with st.container(key="consultas_rapidas"):  # Contenedor de botones de consultas rápidas.
        filas_botones = [BOTONES_FRECUENTES[:4], BOTONES_FRECUENTES[4:]]  # Divide los botones en dos filas.
        for fila in filas_botones:  # Recorre cada fila de botones.
            columnas = st.columns(4)  # Crea cuatro columnas por fila.
            for indice, texto in enumerate(fila):  # Recorre los textos de la fila.
                if columnas[indice].button(texto, key=f"rapido_{texto}", use_container_width=True):  # Si se pulsa...
                    st.session_state.consulta_pendiente = texto  # Guarda la consulta para procesarla.
                    st.session_state.consulta_habilitada = True  # Deja el campo listo para seguir escribiendo.
                    st.rerun()  # Vuelve a ejecutar la app para mostrar la respuesta.

    if st.button("Ver informe final del destino", key="ver_informe_chat"):  # Enlace rápido al resumen.
        guardar_informe_actual()  # Toma el destino seleccionado en el panel lateral.
        st.session_state.mostrar_informe = True  # Marca el informe como visible.
        st.session_state.abrir_informe = True  # Abre el menú del informe.
        st.session_state.abrir_chat = False  # Cierra la ventana del asistente.
        st.session_state.scroll_informe = True  # Desplaza la vista al informe.
        st.rerun()  # Vuelve a ejecutar la app.

    pendiente = st.session_state.pop("consulta_pendiente", None)  # Toma una consulta rápida pendiente.
    if pendiente:  # Si existe una consulta pendiente...
        enviar_consulta(pendiente)  # La procesa.

    with st.container(key="chat_entrada"):  # Agrupa campo y botón en la bandeja inferior.
        if not st.session_state.consulta_habilitada:  # Si aún no se habilitó la escritura...
            st.button(  # Botón inicial que activa el campo de texto.
                "escribir consulta",  # Texto exacto pedido por el usuario.
                key="habilitar_escritura_modal",  # Clave estable del botón.
                on_click=habilitar_escritura,  # Habilita y enfoca el campo.
                type="primary",  # Resalta la acción principal.
                use_container_width=True,  # Ocupa todo el ancho disponible.
            )
        else:  # Si ya se habilitó la escritura...
            with st.form(  # Formulario que permite enviar con la tecla Enter.
                key="formulario_chat",  # Clave estable del formulario.
                clear_on_submit=True,  # Limpia el campo automáticamente después de enviar.
                enter_to_submit=True,  # Enter envía la consulta.
                border=False,  # Sin borde extra dentro de la bandeja.
            ):
                texto = st.text_input(  # Campo normal de texto, más compatible dentro de la ventana modal.
                    "Escriba su consulta...",  # Etiqueta accesible.
                    key="chat_input_modal",  # Clave usada por el botón para tomar el texto.
                    label_visibility="collapsed",  # Oculta la etiqueta visible.
                    placeholder="Escriba su consulta...",  # Texto guía dentro del campo.
                )
                enviado = st.form_submit_button(  # Botón que envía la consulta escrita.
                    "Enviar consulta",  # Texto del botón.
                    key="enviar_consulta_modal",  # Clave estable del botón.
                    type="primary",  # Resalta la acción principal.
                    use_container_width=True,  # Ocupa todo el ancho disponible.
                )
            if enviado:  # Si se envió con clic o con Enter...
                consulta = texto.strip()  # Toma el texto escrito.
                if consulta:  # Si la consulta no está vacía...
                    st.session_state.consulta_pendiente = consulta  # La deja lista para procesar.
                    st.rerun()  # Vuelve a ejecutar para mostrar la respuesta.

    if st.session_state.foco_chat and st.session_state.consulta_habilitada:  # Si el campo recién se habilitó...
        st.html(  # Enfoca el campo para que el teclado aparezca en celular.
            """
            <script>
            setTimeout(function(){
              const campo = document.querySelector('[class*="st-key-chat_entrada"] input');
              if (campo) { campo.focus(); }
            }, 250);
            </script>
            """
        )
        st.session_state.foco_chat = False  # Evita reenfocar en cada respuesta.


@st.fragment(run_every="1s")  # Actualiza automáticamente este fragmento cada segundo.
def panel_proximas(horarios, empresas, cantidad, duracion):  # Muestra tarjetas de próximas salidas.
    ahora = datetime.now(ZONA_HORARIA)  # Obtiene la hora actual en Argentina.
    salidas = construir_salidas(horarios, empresas, ahora, duracion)  # Calcula las próximas salidas.

    st.caption(f"Hora actual: {ahora.strftime('%H:%M:%S')} hs - actualización automática")  # Muestra la hora.
    if not salidas:  # Si no hay salidas para el filtro...
        st.info("No hay horarios cargados para el filtro seleccionado.")  # Muestra aviso.
        return  # Termina la función.

    if all(salida["manana"] for salida in salidas):  # Si todas son de mañana...
        st.info("Ya no quedan salidas para hoy. Se muestran las primeras de mañana.")  # Avisa al usuario.

    for salida in salidas[:cantidad]:  # Muestra solo la cantidad elegida.
        insignia = '<span class="eta-badge">Salida de mañana</span>' if salida["manana"] else ""  # Insignia opcional.
        st.html(  # Inserta una tarjeta HTML con la información de la salida.
            f"""
            <div class="eta-card">
              <div class="eta-hora">{salida['hora']}</div>
              <div>
                <div class="eta-empresa">{html.escape(salida['empresa'])}</div>
                <div class="eta-llegada">Llega aproximadamente a las {salida['llegada']}</div>
              </div>
              <div class="eta-countdown">
                <span class="eta-label">Faltan</span>
                <strong>{formatear_duracion_viva(salida['segundos'])}</strong>
                {insignia}
              </div>
            </div>
            """
        )


st.set_page_config(page_title="Colectivos Abra Pampa", layout="wide")  # Configura título y ancho de la app.

# Inicializa el estado de la navegación simple y de los desplazamientos automáticos.
for clave, valor in (  # Recorre las claves de estado que deben existir desde el inicio.
    ("iniciado", False),  # Indica si el usuario ya pasó por la pantalla de entrada.
    ("abrir_chat", False),  # Abre la ventana modal del asistente desde la burbuja.
    ("foco_chat", False),  # Enfoca el campo de escritura al abrir la ventana.
    ("consulta_habilitada", False),  # Habilita el campo después de pulsar "escribir consulta".
    ("abrir_informe", False),  # Abre el menú del informe final.
    ("mostrar_informe", False),  # Muestra el resumen generado.
    ("scroll_informe", False),  # Desplaza la página hacia el informe final.
):
    if clave not in st.session_state:  # Si la clave no existe todavía...
        st.session_state[clave] = valor  # La crea con su valor inicial.

# Estilos CSS: tema, tarjetas, pantalla de inicio, burbuja flotante y ajustes para celular.
st.html(
    """
    <style>
    @keyframes latido { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
    .app-header { padding: 20px 22px; border-radius: 18px; color: white; margin-bottom: 12px; }
    .app-header-normal { background: linear-gradient(120deg, #1A5CFF, #0F3FA3); }
    .app-header-especial { background: linear-gradient(120deg, #E67E22, #B85D12); }
    .app-header-titulo { font-size: 24px; font-weight: 800; letter-spacing: 0.2px; }
    .app-header-sub { font-size: 13px; opacity: 0.85; margin-top: 2px; }
    .hero-card { background: #FFFFFF; border: 1px solid #D8E1F2; border-radius: 18px; padding: 22px; margin-bottom: 16px; }
    .hero-card h2 { color: #0F3FA3; font-size: 22px; margin: 0 0 8px 0; }
    .hero-card p { color: #5B6B85; margin: 0 0 10px 0; line-height: 1.5; }
    .hero-frase { color: #0F3FA3; font-weight: 600; margin-top: 12px; font-size: 14px; }
    .kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 4px 0 16px 0; }
    .kpi-card { background: #FFFFFF; border: 1px solid #D8E1F2; border-radius: 16px; padding: 12px 16px; }
    .kpi-card span { display: block; font-size: 12px; color: #5B6B85; text-transform: uppercase; letter-spacing: 0.6px; }
    .kpi-card strong { display: block; font-size: 20px; color: #0F3FA3; margin-top: 4px; }
    .dia-especial { background: #FFF3CD; color: #7A4A00; padding: 10px 14px; border-radius: 12px; margin-bottom: 8px; font-size: 14px; }
    .eta-card { display: flex; align-items: center; gap: 16px; background: #FFFFFF; border: 1px solid #D8E1F2; border-left: 5px solid #1A5CFF; border-radius: 16px; padding: 12px 16px; margin: 8px 0; box-shadow: 0 2px 8px rgba(15, 63, 163, 0.08); }
    .eta-hora { font-size: 34px; font-weight: 800; color: #0F3FA3; min-width: 100px; line-height: 1; }
    .eta-empresa { font-weight: 700; color: #111B21; }
    .eta-llegada { font-size: 13px; color: #5B6B85; margin-top: 2px; }
    .eta-countdown { margin-left: auto; text-align: right; }
    .eta-label { display: block; font-size: 11px; color: #5B6B85; text-transform: uppercase; letter-spacing: 0.6px; }
    .eta-countdown strong { font-size: 22px; color: #1A5CFF; }
    .eta-badge { display: inline-block; background: #FFF3CD; color: #7A4A00; border-radius: 999px; padding: 2px 8px; font-size: 11px; margin-top: 4px; }
    [class*="st-key-mensaje_"] [data-testid="stChatMessage"] { border-radius: 14px; padding: 12px 14px; margin: 10px 0; box-shadow: 0 2px 10px rgba(15, 63, 163, 0.10); }
    [class*="st-key-mensaje_asistente_"] [data-testid="stChatMessage"] { background: #EAF2FF !important; border: 1px solid #BFD4FF; border-left: 5px solid #1A5CFF; color: #0F3FA3; }
    [class*="st-key-mensaje_usuario_"] [data-testid="stChatMessage"] { background: #FFF3E6 !important; border: 1px solid #F3D2B3; border-left: 5px solid #E67E22; color: #111B21; }
    [class*="st-key-mensaje_"] [data-testid="stChatMessageContent"] { padding: 2px 4px; }
    [class*="st-key-mensaje_"] [data-testid="stChatMessageContent"] p { margin: 0 0 10px 0; line-height: 1.6; }
    [class*="st-key-mensaje_"] [data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0; }
    [data-testid="stDialog"] > div { border-radius: 18px !important; overflow-y: auto !important; overflow-x: hidden !important; box-shadow: 0 24px 70px rgba(15, 63, 163, 0.35) !important; }
    [class*="st-key-chat_historial"] { display: flex; flex-direction: column; gap: 10px; overflow-y: auto; max-height: 35vh; padding-right: 6px; }
    [class*="st-key-chat_entrada"] { background: #FFFFFF !important; padding: 10px 0 4px 0 !important; border-top: 1px solid #D8E1F2 !important; }
    [class*="st-key-chat_entrada"] input { background: #F7F9FF !important; }
    @media (min-width: 641px) {
      [data-testid="stDialog"] > div { width: min(640px, 62vw) !important; max-width: min(640px, 62vw) !important; height: auto !important; max-height: 86vh !important; }
      [class*="st-key-chat_historial"] { max-height: 30vh; }
    }
    .st-key-consultas_rapidas button { border-radius: 999px; font-size: 13px; }
    .st-key-asistente_bubble, .st-key-asistente_bubble_inicio { position: fixed; right: 16px; bottom: 16px; z-index: 1000; }
    .st-key-asistente_bubble button, .st-key-asistente_bubble_inicio button {
      min-width: 92px; height: 44px; padding: 0 16px; border-radius: 999px;
      background: linear-gradient(135deg, #1A5CFF, #E67E22) !important;
      color: white !important; font-weight: 800 !important;
      border: 2px solid white !important;
      box-shadow: 0 6px 18px rgba(15, 63, 163, 0.35) !important;
    }
    .st-key-asistente_bubble_inicio button {
      box-shadow: 0 0 0 6px rgba(26, 92, 255, 0.18), 0 10px 26px rgba(230, 126, 34, 0.45) !important;
      animation: latido 1.6s ease-in-out infinite;
    }
    .st-key-asistente_bubble_inicio::before {
      content: "Tu asistente"; position: absolute; right: 0; top: -26px;
      background: #0F3FA3; color: white; padding: 4px 10px; border-radius: 999px;
      font-size: 11px; font-weight: 700;
    }
    .main .block-container { padding-bottom: 96px; }
    @media (max-width: 640px) {
      .main .block-container { padding-left: 14px; padding-right: 14px; padding-bottom: 100px; }
      .app-header { padding: 16px; border-radius: 14px; }
      .app-header-titulo { font-size: 20px; }
      .hero-card { padding: 16px; }
      .hero-card h2 { font-size: 19px; }
      .kpi-row { grid-template-columns: 1fr; gap: 8px; }
      .kpi-card { padding: 10px 14px; }
      .kpi-card strong { font-size: 18px; }
      .eta-card { flex-wrap: wrap; gap: 10px; }
      .eta-hora { min-width: auto; font-size: 28px; }
      .eta-countdown { margin-left: 0; text-align: left; width: 100%; }
      [class*="st-key-mensaje_"] [data-testid="stChatMessage"] { padding: 10px; margin: 8px 0; }
      [data-testid="stDialog"] { padding: 0 !important; align-items: stretch !important; }
      [data-testid="stDialog"] > div { width: 100vw !important; max-width: 100vw !important; height: auto !important; max-height: 92dvh !important; margin: 0 !important; border-radius: 0 !important; overflow-y: auto !important; }
      [class*="st-key-chat_historial"] { max-height: 32vh; }
      [class*="st-key-chat_entrada"] { padding: 10px 12px calc(12px + env(safe-area-inset-bottom, 0px)) !important; }
      .st-key-asistente_bubble, .st-key-asistente_bubble_inicio { right: 12px; bottom: 12px; }
      .st-key-asistente_bubble button, .st-key-asistente_bubble_inicio button { min-width: 78px; height: 40px; font-size: 12px; }
    }
    </style>
    """
)

# El encabezado cambia de color cuando hoy es fin de semana o feriado.
clase_encabezado = "app-header-especial" if es_dia_especial() else "app-header-normal"

# La burbuja flotante es el único acceso al chat y abre una ventana modal.
clave_burbuja = "asistente_bubble_inicio" if not st.session_state.iniciado else "asistente_bubble"
if st.button("Asistente", key=clave_burbuja, type="primary"):  # Si se pulsa la burbuja...
    st.session_state.iniciado = True  # Marca la app como iniciada.
    st.session_state.abrir_chat = True  # Abre la ventana del asistente.
    st.session_state.consulta_habilitada = False  # Muestra primero el botón para habilitar la escritura.
    st.session_state.foco_chat = False  # Enfoca el campo recién cuando se habilite.
    st.rerun()  # Vuelve a ejecutar la app.

if not st.session_state.iniciado:  # Muestra la pantalla de entrada la primera vez.
    st.html(  # Presenta la app con una descripción breve y el menú disponible.
        f"""
        <div class="app-header {clase_encabezado}">
          <div class="app-header-titulo">Asistente de Colectivos Abra Pampa</div>
        </div>
        <div class="hero-card">
          <h2>Consultá tus colectivos en un solo lugar</h2>
          <p>Esta app reúne horarios, precios, próximas salidas, encomiendas, terminal, contactos y un asistente que responde preguntas sobre los colectivos de Abra Pampa.</p>
          <p class="hero-frase">Tu viaje empieza acá: horarios, precios y salidas en segundos.</p>
        </div>
        """
    )
    if st.button("Entrar a la app", key="entrar_app", type="primary", use_container_width=True):  # Botón de entrada.
        st.session_state.iniciado = True  # Marca la app como iniciada.
        st.rerun()  # Vuelve a ejecutar la app.
    st.caption("Los horarios y precios pueden cambiar; confirme en la terminal.")  # Aviso de validez.
    st.stop()  # Detiene la app hasta que el usuario ingrese.

st.html(  # Muestra el encabezado principal una vez iniciada la app.
    f"""
    <div class="app-header {clase_encabezado}">
      <div class="app-header-titulo">Asistente de Colectivos Abra Pampa</div>
    </div>
    """
)
st.caption("Los horarios y precios pueden cambiar; confirme en la terminal.")  # Aviso de validez de datos.
st.caption("Abrí el menú lateral para cambiar destino, tipo de día, empresas o cantidad de salidas.")  # Ayuda móvil.

if es_dia_especial():  # Si hoy tiene horario reducido...
    st.html(  # Muestra una franja de aviso.
        '<div class="dia-especial">Hoy hay horarios reducidos por fin de semana o feriado.</div>'
    )

# Se construye la lista de destinos a partir de todas las zonas disponibles.
destinos = [destino for zona in ZONAS.values() for destino in zona["destinos"]]
destino = st.sidebar.selectbox("Destino", destinos)  # Permite elegir el destino principal.
tipo = st.sidebar.selectbox(  # Permite forzar el tipo de día.
    "Tipo de día",
    ["Automático", "Día de semana", "Fin de semana / feriado"],
)
tipo_clave = {  # Convierte la etiqueta visible a la clave usada por el módulo NLP.
    "Automático": None,  # Usa el día real.
    "Día de semana": "semana",  # Fuerza horario normal.
    "Fin de semana / feriado": "finde",  # Fuerza horario reducido.
}[tipo]
horarios = horarios_destino(destino, tipo_clave)  # Obtiene los horarios según destino y tipo de día.
empresas = st.sidebar.multiselect(  # Filtra las empresas que se mostrarán.
    "Empresas",
    options=list(horarios),  # Opciones tomadas del diccionario de horarios.
    default=list(horarios),  # Todas seleccionadas por defecto.
    key=f"empresas_{destino}_{tipo_clave}",  # Clave única por destino y tipo de día.
)
cantidad = st.sidebar.number_input(  # Define cuántas próximas salidas se mostrarán.
    "Cantidad de próximas salidas",
    min_value=1,  # Mínimo una salida.
    max_value=10,  # Máximo diez salidas.
    value=3,  # Valor inicial.
)

st.session_state.destino_actual = destino  # Guarda el destino vigente para usarlo en el informe.
st.session_state.tipo_actual = tipo_clave  # Guarda el tipo de día vigente.
st.session_state.empresas_actuales = list(empresas)  # Guarda las empresas vigentes.
st.session_state.cantidad_actual = cantidad  # Guarda la cantidad vigente.

st.html(  # Muestra los indicadores principales: destino, precio y duración.
    f"""
    <div class="kpi-row">
      <div class="kpi-card"><span>Destino</span><strong>{html.escape(destino)}</strong></div>
      <div class="kpi-card"><span>Precio</span><strong>{PRECIOS[destino]}</strong></div>
      <div class="kpi-card"><span>Duración</span><strong>{formatear_duracion(DURACION_MIN[destino])}</strong></div>
    </div>
    """
)

# Cada menú es un desplegable independiente, uno debajo del otro.
# El chat no figura en el menú principal: solo se abre desde la burbuja flotante.

with st.expander("Horarios"):  # Menú de horarios.
    st.subheader(f"Horarios hacia {destino}")  # Título con el destino elegido.
    st.caption(encabezado_dia(tipo_clave))  # Explica si el horario es normal o reducido.
    columnas = st.columns(2)  # Crea dos columnas para las métricas.
    columnas[0].metric("Duración estimada", formatear_duracion(DURACION_MIN[destino]))  # Muestra duración.
    columnas[1].metric("Precio del boleto", PRECIOS[destino])  # Muestra precio.
    filas = [  # Arma las filas de la tabla de horarios.
        {"Empresa": empresa, "Horarios": " - ".join(horas) + " hs"}
        for empresa, horas in horarios.items()
        if empresa in empresas
    ]
    if filas:  # Si hay filas para mostrar...
        st.dataframe(filas, hide_index=True, width="stretch")  # Muestra la tabla sin índice.
    else:  # Si el filtro dejó la tabla vacía...
        st.info("Seleccione al menos una empresa en el panel lateral.")  # Pide seleccionar empresas.
    if usa_horario_reducido(tipo_clave):  # Si corresponde horario reducido...
        st.info(MSG_NOTA_REDUCIDO)  # Muestra la nota de advertencia.
    st.caption(f"Zona: {zona_de(destino)} - salidas desde la Terminal de Abra Pampa.")  # Muestra la zona.

with st.expander("Próximas salidas"):  # Menú de cuenta regresiva.
    st.subheader(f"Próximas salidas hacia {destino}")  # Título con el destino elegido.
    panel_proximas(horarios, empresas, cantidad, DURACION_MIN[destino])  # Dibuja el panel con contador.

with st.expander("Precios"):  # Menú de precios.
    st.subheader(f"Precio actual: {PRECIOS[destino]}")  # Muestra el precio del destino principal.
    for clave, zona in ZONAS.items():  # Recorre las zonas.
        with st.expander(zona["titulo"], expanded=True):  # Muestra cada zona desplegable.
            filas_precios = [  # Arma una fila por destino con precio y duración.
                {
                    "Destino": destino_precio,
                    "Precio": PRECIOS[destino_precio],
                    "Duración": formatear_duracion(DURACION_MIN[destino_precio]),
                }
                for destino_precio in zona["destinos"]
            ]
            st.dataframe(filas_precios, hide_index=True, width="stretch")  # Muestra la tabla de precios.
    st.caption("El precio es el mismo en todas las empresas y se abona en boletería.")  # Aclara el precio.

with st.expander("Comparar"):  # Menú de comparación.
    destino_comparar = st.selectbox("Destino a comparar", destinos, key="comparar_destino")  # Elige destino.
    st.text(txt_comparar(destino_comparar))  # Muestra la comparación de empresas.

with st.expander("Encomiendas"):  # Menú de envíos.
    st.text(txt_envios())  # Muestra empresas que hacen envíos.
    st.subheader("Requisitos para enviar (Balut)")  # Título de la lista de requisitos.
    confirmaciones = []  # Guarda el estado de los checkboxes.
    for grupo, items in REQUISITOS_ENCOMIENDAS.items():  # Recorre cada grupo de requisitos.
        with st.expander(grupo, expanded=True):  # Muestra el grupo desplegable.
            for item in items:  # Recorre cada requisito del grupo.
                confirmaciones.append(st.checkbox(item, key=f"enc_{grupo}_{item}"))  # Agrega el checkbox.
    completados = sum(confirmaciones)  # Cuenta cuántos requisitos fueron confirmados.
    st.progress(  # Muestra una barra de progreso.
        completados / len(confirmaciones),  # Calcula la proporción completada.
        text=f"{completados}/{len(confirmaciones)} requisitos confirmados",  # Texto de la barra.
    )
    st.caption("Confirme las condiciones con la empresa antes de enviar la encomienda.")  # Aviso final.

with st.expander("Terminal y pagos"):  # Menú de terminal y pago.
    st.text(txt_terminal())  # Muestra datos de la terminal.
    st.subheader("Forma de pago")  # Título de la forma de pago.
    st.text(txt_forma_pago())  # Muestra medios de pago.
    with st.expander("Requisitos para viajar"):  # Sección desplegable de requisitos.
        st.text(txt_requisitos())  # Muestra requisitos.
    with st.expander("DNI digital"):  # Sección desplegable de DNI digital.
        st.text(txt_documento_digital())  # Muestra información de DNI digital.
    with st.expander("Mascotas"):  # Sección desplegable de mascotas.
        st.text(txt_mascotas())  # Muestra información sobre mascotas.

with st.expander("Contacto"):  # Menú de contactos.
    st.caption(f"Boletería: {HORARIO_BOLETERIA}")  # Muestra el horario de boletería.
    for empresa, telefono in CONTACTOS.items():  # Recorre las empresas y sus teléfonos.
        with st.container(border=True):  # Dibuja una tarjeta por empresa.
            columnas = st.columns([2, 1, 1])  # Crea columnas para nombre y botones.
            columnas[0].write(empresa)  # Muestra el nombre de la empresa.
            columnas[0].code(telefono)  # Muestra el teléfono con estilo de código.
            columnas[1].link_button("Llamar", f"tel:+54{telefono}")  # Enlace para llamar.
            columnas[2].link_button("WhatsApp", f"https://wa.me/549{telefono}")  # Enlace a WhatsApp.
    st.caption("Empresas con envíos: " + ", ".join(EMPRESAS_ENVIOS) + ". Verifique los datos antes de publicar.")

with st.expander("Preguntas frecuentes"):  # Menú de FAQ.
    st.text(txt_preguntas_frecuentes())  # Muestra el texto de preguntas frecuentes.

# El informe final queda al final de toda la app y resume el destino seleccionado.
st.html('<div id="seccion-informe"></div>')  # Ancla para desplazarse al informe.
with st.expander("Informe final", expanded=st.session_state.abrir_informe):  # Menú de resumen.
    st.caption("Genera un resumen con los datos básicos del destino elegido.")  # Explica el menú.
    if st.button("Generar informe final", key="generar_informe"):  # Botón que arma el resumen.
        guardar_informe_actual()  # Toma el destino seleccionado en el panel lateral.
        st.session_state.mostrar_informe = True  # Marca el informe como visible.
        st.session_state.abrir_informe = True  # Mantiene abierto el menú.
        st.rerun()  # Vuelve a ejecutar la app.
    if st.session_state.mostrar_informe:  # Si ya se generó el informe...
        destino_informe = st.session_state.get("informe_destino", destino)  # Destino usado en el informe.
        tipo_informe = st.session_state.get("informe_tipo", tipo_clave)  # Tipo de día usado.
        empresas_informe = st.session_state.get("informe_empresas", empresas)  # Empresas usadas.
        cantidad_informe = st.session_state.get("informe_cantidad", cantidad)  # Cantidad usada.
        horarios_informe = horarios_destino(destino_informe, tipo_informe)  # Horarios del destino guardado.
        informe = construir_informe_final(  # Construye el texto del resumen.
            destino_informe,  # Destino elegido al generar.
            tipo_informe,  # Tipo de día elegido al generar.
            horarios_informe,  # Horarios del destino elegido.
            empresas_informe,  # Empresas filtradas al generar.
            cantidad_informe,  # Cantidad de salidas elegida.
            DURACION_MIN[destino_informe],  # Duración del destino elegido.
        )
        clave_informe = (  # Clave única para que el cuadro se renueve con cada selección.
            f"{destino_informe}_{tipo_informe}_{cantidad_informe}_{'-'.join(empresas_informe)}"
        )
        st.caption(f"Resumen generado para: {destino_informe}")  # Muestra el destino usado.
        st.text_area(  # Muestra el informe con el destino elegido.
            "Resumen del destino",  # Etiqueta del cuadro.
            informe,  # Texto del informe.
            height=360,  # Altura del cuadro.
            key=f"informe_final_texto_{clave_informe}",  # Clave cambiante por selección.
        )
        st.download_button(  # Permite guardar el informe como texto.
            "Descargar informe .txt",  # Etiqueta del botón.
            informe,  # Contenido del archivo.
            file_name=f"informe_{destino_informe.lower().replace(' ', '_')}.txt",  # Nombre del archivo.
            key=f"descargar_informe_{clave_informe}",  # Clave cambiante por selección.
        )

# Abre la ventana del asistente solo cuando se pulsa la burbuja flotante.
if st.session_state.abrir_chat:  # Si hay un pedido pendiente...
    ventana_chat()  # Muestra el chat en una ventana modal.

# Desplaza la vista hacia la sección pedida después de que Streamlit dibujó la página.
if st.session_state.scroll_informe:  # Si se pidió ir al informe...
    st.html(  # Ejecuta el desplazamiento suave.
        "<script>setTimeout(function(){document.getElementById('seccion-informe')?.scrollIntoView({behavior:'smooth', block:'start'});}, 120);</script>"
    )
    st.session_state.scroll_informe = False  # Limpia la bandera para no repetirlo.
