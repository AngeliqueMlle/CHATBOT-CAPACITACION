"""Definición de todos los módulos de capacitación de CECOM."""

MODULOS = {
    "plataformas": [
        {
            "nombre": "App de Incidencias",
            "tipo": "plataforma",
            "resumen": "Plataforma para el registro y gestión de incidentes operativos en tiempo real.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá el manual de uso de la App de Incidencias: "
                "cómo crear un nuevo incidente, campos obligatorios (tipo, ubicación, prioridad, descripción), "
                "estados posibles del incidente (abierto, en proceso, cerrado, derivado), "
                "cómo asignar responsables a un incidente, "
                "consulta y filtrado del historial de incidentes, "
                "generación de reportes por período o tipo de incidente, "
                "y procedimientos de escalamiento cuando un incidente no se resuelve en tiempo."
            )
        },
        {
            "nombre": "Sistema de Validación",
            "tipo": "plataforma",
            "resumen": "Sistema de validación de personal y control de accesos institucionales.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía del Sistema de Validación: "
                "cómo registrar el ingreso y egreso de personal, "
                "tipos de credenciales reconocidas por el sistema (DNI, tarjeta RFID, biométrico), "
                "proceso de alta y baja de usuarios en el sistema, "
                "consulta de registros de acceso por persona o por rango de fechas, "
                "procedimiento ante credencial no reconocida o acceso denegado, "
                "y cómo generar reportes de asistencia para supervisores."
            )
        },
        {
            "nombre": "Sistema de Cazadores",
            "tipo": "plataforma",
            "resumen": "Plataforma de seguimiento y control de operativos en campo.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá el manual del Sistema de Cazadores: "
                "cómo crear y gestionar operativos de campo, "
                "asignación de agentes a operativos activos, "
                "seguimiento en tiempo real de la ubicación de los agentes, "
                "registro de novedades durante el operativo, "
                "estados del operativo (planificado, activo, finalizado), "
                "y generación de informes de resultado al cierre de cada operativo."
            )
        },
        {
            "nombre": "Mapa CECOM",
            "tipo": "plataforma",
            "resumen": "Plataforma de visualización geográfica de las 611 cámaras municipales activas.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía del Mapa CECOM: "
                "cómo visualizar las 611 cámaras municipales en el mapa interactivo, "
                "filtros disponibles por zona, tipo de cámara (domo, PTZ, LPR) y estado (activa, inactiva), "
                "cómo acceder al stream en vivo de una cámara desde el mapa, "
                "uso de la capa de incidentes superpuesta al mapa, "
                "cómo buscar una cámara por dirección o código, "
                "y exportación de capturas o clips de video desde el mapa."
            )
        },
        {
            "nombre": "Gestionate",
            "tipo": "plataforma",
            "resumen": "Sistema de gestión administrativa del personal municipal.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá el manual de Gestionate: "
                "cómo registrar y actualizar datos del personal municipal, "
                "gestión de legajos digitales (documentos, contratos, capacitaciones), "
                "solicitud y aprobación de licencias y permisos, "
                "módulo de evaluación de desempeño, "
                "generación de reportes de plantel por área o turno, "
                "y procedimientos para el alta y baja de agentes en el sistema."
            )
        },
        {
            "nombre": "Centinela",
            "tipo": "plataforma",
            "resumen": "Plataforma de monitoreo y generación de alertas de seguridad.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía de Centinela: "
                "cómo configurar reglas de alerta (intrusión, merodeo, aglomeración), "
                "visualización del panel de alertas activas en tiempo real, "
                "respuesta y cierre de alertas por parte del operador, "
                "integración con las cámaras para visualización inmediata del evento, "
                "niveles de criticidad de alerta y protocolos de escalamiento, "
                "y generación de reportes históricos de alertas por zona o período."
            )
        },
        {
            "nombre": "Hikvision WebClient",
            "tipo": "plataforma",
            "resumen": "Acceso web a las cámaras Hikvision desde cualquier navegador.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía de Hikvision WebClient: "
                "cómo iniciar sesión desde el navegador sin instalar software adicional, "
                "navegación por grupos de cámaras y visualización en grilla (1, 4, 9, 16 canales), "
                "control PTZ desde el cliente web (pan, tilt, zoom), "
                "reproducción de grabaciones con búsqueda por fecha y hora, "
                "descarga de clips de video, "
                "y requisitos de navegador y resolución de problemas de conexión."
            )
        },
        {
            "nombre": "HikCentral Professional",
            "tipo": "plataforma",
            "resumen": (
                "Plataforma principal de monitoreo y videovigilancia de CECOM. "
                "Concentra el acceso a las 611 cámaras del distrito organizadas por jurisdicción, "
                "con visualización en vivo, reproducción de grabaciones y respuesta a incidentes en tiempo real.\n\n"
                "Funciones disponibles:\n"
                "• Visualización y control de cámaras por zona geográfica\n"
                "• Sistema LPR — detección y registro de placas vehiculares\n"
                "• Gestionar rostros y bibliotecas de personas buscadas\n"
                "• Altavoces en modo broadcast y comunicación bidireccional\n"
                "• Control PTZ para cámaras domo\n"
                "• Búsqueda de personas por rango de tiempo y cámara\n\n"
                "Para mayor información revisa el material completo."
            ),
            "pdf": "/static/modules/hikcentral_professional/manual_hikcentral_professional.pdf",
            "video": None,
            "preview": "/static/modules/hikcentral_professional/hikcentral_professional.png"
        },
        {
            "nombre": "IVMS-4200",
            "tipo": "plataforma",
            "resumen": "Plataforma para la gestión y monitoreo de cámaras vecinales.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía de IVMS-4200: "
                "instalación del cliente en PC, "
                "agregar dispositivos y organizar grupos de cámaras vecinales, "
                "monitoreo en vivo con distribución de pantalla personalizable, "
                "reproducción y búsqueda de grabaciones por evento o período, "
                "configuración de detección de movimiento y otras reglas de video, "
                "y procedimientos de mantenimiento básico (reinicio de dispositivo, verificación de conexión)."
            )
        },
        {
            "nombre": "SmartPSS",
            "tipo": "plataforma",
            "resumen": "Plataforma de escritorio Dahua para monitoreo y gestión de dispositivos.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá el manual de SmartPSS: "
                "instalación y configuración del cliente Dahua SmartPSS, "
                "incorporación de cámaras y otros dispositivos Dahua al sistema, "
                "monitoreo en vivo con hasta 64 canales simultáneos, "
                "configuración de grabación por movimiento o calendario, "
                "búsqueda y exportación de grabaciones, "
                "gestión de alarmas y notificaciones push, "
                "y actualización de firmware de dispositivos desde la plataforma."
            )
        },
        {
            "nombre": "PUC",
            "tipo": "plataforma",
            "resumen": "Plataforma unificada de control para la gestión centralizada.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía del PUC (Plataforma Unificada de Control): "
                "acceso y autenticación en el panel centralizado, "
                "integración de múltiples sistemas bajo una sola interfaz, "
                "monitoreo unificado de alertas provenientes de distintas plataformas, "
                "asignación y seguimiento de tareas entre operadores, "
                "visualización de estadísticas operativas en tiempo real, "
                "y procedimientos de contingencia ante falla de algún subsistema integrado."
            )
        },
        {
            "nombre": "Geosatelital",
            "tipo": "plataforma",
            "resumen": "Sistema de rastreo satelital de unidades municipales en tiempo real.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía de Geosatelital: "
                "cómo visualizar en el mapa la posición en tiempo real de las unidades municipales, "
                "historial de recorridos por unidad y por período, "
                "configuración de geocercas y alertas por salida de zona autorizada, "
                "consulta de velocidad, paradas y tiempo de inactividad de cada unidad, "
                "generación de reportes de flota para supervisores, "
                "y procedimiento ante señal perdida o unidad sin reporte."
            )
        }
    ],
    "dispositivos": [
        {
            "nombre": "Radio Dolphin",
            "tipo": "dispositivo",
            "resumen": "Radio de comunicación utilizada por el personal operativo en campo.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá el manual de la Radio Dolphin: "
                "encendido y apagado correcto del equipo, "
                "selección de canal de comunicación según el área operativa, "
                "uso del botón PTT (Push To Talk) y protocolo de comunicación por radio, "
                "ajuste de volumen y silenciador (squelch), "
                "procedimiento de carga de batería y duración estimada, "
                "cuidado y mantenimiento básico del equipo, "
                "y qué hacer si el equipo no establece comunicación o presenta fallas."
            )
        },
        {
            "nombre": "Bodycam",
            "tipo": "dispositivo",
            "resumen": "Cámara corporal utilizada por los agentes durante operativos en campo.",
            "pdf": None,
            "video": None,
            "preview": None,
            "contexto": (
                "[PLACEHOLDER] Aquí irá la guía de uso de la Bodycam: "
                "cómo encender la cámara y verificar que está grabando (indicador LED), "
                "correcta colocación del dispositivo en el chaleco o uniforme, "
                "inicio y detención manual de grabación, "
                "capacidad de almacenamiento y tiempo de grabación continua, "
                "procedimiento de descarga de grabaciones al finalizar el turno, "
                "carga de batería y tiempo estimado, "
                "y protocolo de uso obligatorio durante operativos (cuándo activarla, cuándo no)."
            )
        }
    ]
}
