import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Listas para generar nombres de juegos semi-realistas
_PREFIJOS = [
    'Shadow', 'Dark', 'Neon', 'Cyber', 'Iron', 'Star', 'Blood', 'Crystal',
    'Phantom', 'Storm', 'Solar', 'Frozen', 'Golden', 'Lost', 'Final',
    'Hyper', 'Mega', 'Ultra', 'Chrono', 'Eternal', 'Mystic', 'Savage',
    'Grand', 'Epic', 'Wild', 'Rogue', 'Silent', 'Ancient', 'Inferno', 'Turbo'
]
_SUFIJOS = [
    'Quest', 'Wars', 'Legends', 'Chronicles', 'Rising', 'Odyssey', 'Arena',
    'Frontier', 'Tactics', 'Horizon', 'Saga', 'Legacy', 'Fury', 'Reborn',
    'Evolution', 'Worlds', 'Strike', 'Assault', 'Dominion', 'Vanguard',
    'Blade', 'Force', 'Protocol', 'Drift', 'Reign', 'Nexus', 'Forge',
    'Hunters', 'Empire', 'Zero'
]


def _generar_titulo(idx):
    """Genera un nombre de videojuego combinando prefijo + sufijo."""
    p = _PREFIJOS[idx % len(_PREFIJOS)]
    s = _SUFIJOS[idx % len(_SUFIJOS)]
    # Evitar que se repitan muchos: si coinciden rotación, meter número de serie
    if idx >= len(_PREFIJOS) * len(_SUFIJOS):
        return f'{p} {s} {idx // (len(_PREFIJOS) * len(_SUFIJOS)) + 1}'
    return f'{p} {s}'


def generar_dataset(num_registros=5000):
    """Genera un dataset sintético robusto simulando ventas globales de videojuegos."""
    np.random.seed(42)
    random.seed(42)

    plataformas = ['PS5', 'Xbox Series X', 'PC', 'Nintendo Switch', 'PS4', 'Xbox One', 'Mobile']
    generos = ['Accion', 'Shooter', 'RPG', 'Deportes', 'Aventura', 'Estrategia', 'Simulacion', 'Puzzle']
    publishers = [
        'Nintendo', 'EA', 'Activision', 'Sony', 'Microsoft',
        'Ubisoft', 'Take-Two', 'Square Enix', 'Tencent'
    ]

    # Rango de lanzamiento: ~5 años (2019-2024)
    base_date = datetime(2019, 1, 1)
    fechas = [base_date + timedelta(days=random.randint(0, 1800)) for _ in range(num_registros)]

    data = []
    for i in range(num_registros):
        plat = random.choice(plataformas)
        pub = random.choice(publishers)
        gen = random.choice(generos)
        fecha = fechas[i]

        # Puntuación base con distribución normal centrada en 70
        critica = np.random.normal(loc=70, scale=15)

        # Multiplicador: juegos mejor calificados venden más
        mult = max(0.1, critica / 70.0)

        ventas_na = np.random.exponential(scale=1.5) * mult
        ventas_eu = np.random.exponential(scale=1.2) * mult
        ventas_jp = np.random.exponential(scale=0.5) * mult
        ventas_otros = np.random.exponential(scale=0.3) * mult

        # Lógica de negocio: sesgo regional por publisher/plataforma
        if pub == 'Nintendo' or plat == 'Nintendo Switch':
            ventas_jp *= 2.5
        if gen == 'Shooter':
            ventas_na *= 1.8
            ventas_eu *= 1.5

        # Estacionalidad: lanzamientos de Q4 venden mejor (temporada navideña)
        if fecha.month in [10, 11, 12]:
            ventas_na *= 1.2
            ventas_eu *= 1.2

        # Puntuación de usuarios derivada de la crítica con ruido
        score_usuarios = critica / 10.0 + np.random.normal(0, 0.5)

        data.append({
            'ID_Juego': f'GME-{str(i + 1).zfill(5)}',
            'Titulo': _generar_titulo(i),
            'Plataforma': plat,
            'Genero': gen,
            'Publisher': pub,
            'Fecha_Lanzamiento': fecha,
            'Ventas_NA_Millones': ventas_na,
            'Ventas_EU_Millones': ventas_eu,
            'Ventas_JP_Millones': ventas_jp,
            'Ventas_Otros_Millones': ventas_otros,
            'Puntuacion_Critica': critica,
            'Puntuacion_Usuarios': score_usuarios
        })

    df = pd.DataFrame(data)

    # Inyectar errores simulados para validar el pipeline de limpieza
    idx_critica = np.random.choice(df.index, size=250, replace=False)
    idx_publisher = np.random.choice(df.index, size=100, replace=False)
    idx_neg = np.random.choice(df.index, size=30, replace=False)

    df.loc[idx_critica, 'Puntuacion_Critica'] = np.nan
    df.loc[idx_critica, 'Puntuacion_Usuarios'] = np.nan  # Ambas columnas se ensucian juntas
    df.loc[idx_publisher, 'Publisher'] = np.nan
    df.loc[idx_neg, 'Ventas_NA_Millones'] = -0.5

    return df


def limpiar_datos(df):
    """Limpia, formatea y normaliza el dataframe para consumo en BI."""
    print('Iniciando limpieza de datos...')

    df_clean = df.copy()

    # 1. Imputar nulos: media para numéricas, constante para categóricas
    media_critica = df_clean['Puntuacion_Critica'].mean()
    media_usuarios = df_clean['Puntuacion_Usuarios'].mean()
    df_clean['Puntuacion_Critica'] = df_clean['Puntuacion_Critica'].fillna(media_critica)
    df_clean['Puntuacion_Usuarios'] = df_clean['Puntuacion_Usuarios'].fillna(media_usuarios)
    df_clean['Publisher'] = df_clean['Publisher'].fillna('Desconocido')

    # 2. Corregir ventas negativas (errores de carga)
    cols_ventas = [
        'Ventas_NA_Millones', 'Ventas_EU_Millones',
        'Ventas_JP_Millones', 'Ventas_Otros_Millones'
    ]
    for col in cols_ventas:
        df_clean[col] = df_clean[col].clip(lower=0)

    # 3. Acotar puntuaciones a rangos válidos
    df_clean['Puntuacion_Critica'] = df_clean['Puntuacion_Critica'].clip(0, 100).round(0).astype(int)
    df_clean['Puntuacion_Usuarios'] = df_clean['Puntuacion_Usuarios'].clip(0, 10).round(1)

    # 4. Columna calculada: ventas globales
    df_clean['Ventas_Globales_Millones'] = (
        df_clean['Ventas_NA_Millones']
        + df_clean['Ventas_EU_Millones']
        + df_clean['Ventas_JP_Millones']
        + df_clean['Ventas_Otros_Millones']
    )

    # 5. Extraer componentes de fecha para facilitar filtros en BI
    df_clean['Anio_Lanzamiento'] = df_clean['Fecha_Lanzamiento'].dt.year
    df_clean['Mes_Lanzamiento'] = df_clean['Fecha_Lanzamiento'].dt.month
    df_clean['Trimestre'] = df_clean['Fecha_Lanzamiento'].dt.quarter

    # 6. Redondear ventas a 2 decimales
    cols_ventas.append('Ventas_Globales_Millones')
    df_clean[cols_ventas] = df_clean[cols_ventas].round(2)

    # 7. Eliminar duplicados si existen
    antes = len(df_clean)
    df_clean = df_clean.drop_duplicates(subset='ID_Juego')
    despues = len(df_clean)
    if antes != despues:
        print(f'  -> Se eliminaron {antes - despues} filas duplicadas.')

    # 8. Resetear índice
    df_clean = df_clean.reset_index(drop=True)

    print(f'Limpieza finalizada. Registros finales: {len(df_clean)}')
    return df_clean


if __name__ == '__main__':
    print('Generando dataset...')
    df_raw = generar_dataset(num_registros=8500)

    df_clean = limpiar_datos(df_raw)

    output_path = 'datos_limpios.csv'
    df_clean.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Exportado a '{output_path}' ({len(df_clean)} filas)")
