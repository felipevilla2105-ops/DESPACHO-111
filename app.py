import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import io

# Configuración de la página
st.set_page_config(
    page_title="Clasificador de Procesos Judiciales",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Definición de Nombres de Columna según tu matriz ---
COL_ACTUACION = 'Última Actuación'
COL_FECHA = 'Fecha Actuación' 
COL_CASO = 'Número Noticia'   

def procesar_datos(df):
    """Realiza la limpieza, clasificación y cálculo de procesos atrasados."""
    try:
        # 1.0 LIMPIEZA ADICIONAL: Eliminar comillas simples de 'Número Noticia'
        # Esto asegura que el ID del caso se muestre limpio.
        if COL_CASO in df.columns and df[COL_CASO].dtype == 'object':
            df[COL_CASO] = df[COL_CASO].astype(str).str.replace("'", "", regex=False)
        
        # 1.1 Preparación de datos: Convertir la columna de fecha a formato datetime
        df[COL_FECHA] = pd.to_datetime(df[COL_FECHA], errors='coerce')
        
        # Eliminar filas con fechas no válidas
        df.dropna(subset=[COL_FECHA], inplace=True)
        
        # 2. Obtener lista única de actuaciones
        lista_actuaciones = df[COL_ACTUACION].unique().tolist()
        lista_actuaciones.sort() # Ordenar alfabéticamente
        
        # 3. Clasificación por Fecha (Reciente a Antigua)
        df_clasificado_fecha = df.sort_values(by=COL_FECHA, ascending=False)
        
        # 4. Procesos con Última Actuación hace más de 2 meses
        
        # Usar .replace() para poner la hora en cero (medianoche)
        fecha_actual = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calcular la fecha límite: hace 2 meses a partir de hoy.
        fecha_limite = fecha_actual - relativedelta(months=2)

        # Filtrar los procesos
        procesos_atrasados = df[df[COL_FECHA].dt.floor('D') < fecha_limite]
        
        if not procesos_atrasados.empty:
            # Calcular la antigüedad en días y ordenar
            procesos_atrasados['Días de Antigüedad'] = (fecha_actual - procesos_atrasados[COL_FECHA]).dt.days
            
            # Seleccionar columnas clave y ordenar por los más antiguos
            resultado_atrasados = procesos_atrasados[[
                COL_CASO,
                COL_FECHA, 
                COL_ACTUACION, 
                'Días de Antigüedad'
            ]].sort_values(by='Días de Antigüedad', ascending=False)
        else:
            resultado_atrasados = pd.DataFrame()
            
        return lista_actuaciones, df, df_clasificado_fecha, resultado_atrasados, fecha_actual, fecha_limite

    except KeyError as e:
        st.error(f"Error: No se encontró la columna clave requerida. Asegúrate de que tu archivo contenga las columnas '{COL_CASO}', '{COL_FECHA}' y '{COL_ACTUACION}'. Detalles: {e}")
        return None, None, None, None, None, None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante el procesamiento de datos: {e}")
        return None, None, None, None, None, None


# --- Estructura de la Aplicación Streamlit ---

st.title("Sistema de Clasificación y Seguimiento de Procesos 🧑‍⚖️")
st.markdown("""
Esta herramienta te ayuda a analizar tu archivo CSV de procesos judiciales.
""")

# Carga de archivos
uploaded_file = st.file_uploader(
    "📂 Sube tu archivo CSV de procesos", 
    type="csv"
)

if uploaded_file is not None:
    # Leer el archivo CSV
    df_original = pd.read_csv(uploaded_file)
    
    # Procesar los datos para obtener la lista de actuaciones y los DataFrames
    lista_actuaciones, df_completo, df_clasificado_fecha, procesos_atrasados, fecha_actual, fecha_limite = procesar_datos(df_original.copy())

    if lista_actuaciones is not None:
        
        # ----------------------------------------------------
        # BARRA LATERAL (Sidebar) para la selección del usuario
        # ----------------------------------------------------
        st.sidebar.header("🔍 Filtro de Actuaciones")
        st.sidebar.markdown(f"Selecciona una o varias actuaciones de la columna **{COL_ACTUACION}**.")
        
        # El usuario selecciona las actuaciones
        actuaciones_seleccionadas = st.sidebar.multiselect(
            f'Elige las actuaciones que deseas ver:',
            options=lista_actuaciones,
            default=lista_actuaciones 
        )

        st.divider()

        # ----------------------------------------------------
        # APARTE 1: Clasificación Filtrada
        # ----------------------------------------------------
        st.header("1. Clasificación de Procesos")
        st.markdown(f"Tabla que muestra los procesos filtrados y ordenados por fecha de actuación (**{COL_FECHA}**, más reciente primero).")
        
        # Aplicar el filtro de las actuaciones seleccionadas
        if actuaciones_seleccionadas:
            df_filtrado_clasificado = df_clasificado_fecha[df_clasificado_fecha[COL_ACTUACION].isin(actuaciones_seleccionadas)]
        else:
            df_filtrado_clasificado = pd.DataFrame()
            st.warning(f"Selecciona al menos una '{COL_ACTUACION}' en el menú de la izquierda para ver los resultados.")


        if not df_filtrado_clasificado.empty:
            st.subheader(f"Mostrando {len(df_filtrado_clasificado)} procesos con las actuaciones seleccionadas")
            # Mostrar la tabla filtrada y ordenada por Fecha
            st.dataframe(df_filtrado_clasificado[[COL_CASO, COL_ACTUACION, COL_FECHA]], use_container_width=True)
            
            # Opción de descarga
            csv_filtrado = df_filtrado_clasificado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Procesos Clasificados y Filtrados",
                data=csv_filtrado,
                file_name='procesos_clasificados_filtrados.csv',
                mime='text/csv',
            )

        st.divider()

        # ----------------------------------------------------
        # APARTE 2: Procesos con inactividad > 2 meses
        # ----------------------------------------------------
        st.header("2. Alerta de Inactividad: Procesos con más de 2 Meses sin Actuación")
        
        st.info(
            f"La fecha de referencia es **Hoy ({fecha_actual.strftime('%d-%m-%Y')})**. "
            f"El límite de tiempo para ser clasificado como 'atrasado' es **{fecha_limite.strftime('%d-%m-%Y')}**."
        )

        if not procesos_atrasados.empty:
            st.success(f"🚨 **¡ATENCIÓN! Se encontraron {len(procesos_atrasados)} procesos con inactividad mayor a 2 meses.**")
            
            # Mostrar la tabla de resultados
            st.dataframe(procesos_atrasados, use_container_width=True, hide_index=True)
            
            # Opción de descarga
            csv_atrasados = procesos_atrasados.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Listado de Procesos Atrasados",
                data=csv_atrasados,
                file_name='procesos_atrasados_mas_de_2_meses.csv',
                mime='text/csv',
            )
        else:
            st.balloons()
            st.success("🎉 **¡Excelente!** Todos los procesos tienen una 'Última Actuación' dentro de los últimos dos meses.")
            