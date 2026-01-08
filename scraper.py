import pandas as pd
from datetime import datetime
import time
import os
from datetime import timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
# CONFIG SELENIUM (compatible con GitHub Actions Ubuntu)
def get_driver():
    chrome_options = Options()
    chrome_options.page_load_strategy = 'eager'
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(r"C:\tools\chromedriver-win64\chromedriver.exe")
    return webdriver.Chrome(service=service,options=chrome_options)
    
# FUNCIONES COMUNES
def escribir_fecha(input_element, fecha_string):
    input_element.click()
    input_element.send_keys(Keys.CONTROL, "a")
    input_element.send_keys(Keys.BACKSPACE)
    input_element.send_keys(fecha_string)
    time.sleep(0.1)

def cargar_iframe(driver):
    
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.TAG_NAME, "iframe"))
    )

    WebDriverWait(driver, 30).until(
        EC.frame_to_be_available_and_switch_to_it(
            (By.XPATH, "//iframe[contains(@src,'emmsa')]")
        )
    )
    
# SCRAPING PRECIOS DIARIOS
def scraper_precios(driver, fecha_hoy):

    print("🔎 Scraping PRECIOS...")

    url = "https://www.emmsa.com.pe/index.php/precios-diarios/"
    driver.get(url)

    cargar_iframe(driver)

    fecha_input = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "txtfecha1"))
    )
    
    escribir_fecha(fecha_input, fecha_hoy)
    
    driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/table/tbody/tr[2]/td/table/tbody/tr/td[1]/input").click()
    
    try:
        WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "chkChanging"))
         ).click()
    except:
        pass

    boton = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Consultar')]"))
    )
    boton.click()
    
    time.sleep(1)

    driver.switch_to.default_content()
    cargar_iframe(driver)

    # Leer la tabla
    try:
        tabla = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "timecard"))
        )
    except:
        print("⚠ No hay tabla de precios")
        return None

    headers = [
        th.text.strip()
        for th in tabla.find_elements(By.TAG_NAME, "th")
        if th.text.strip() != "Precios x Kg en S/"
    ]

    filas = tabla.find_elements(By.XPATH, ".//tr[td]")
    datos = []

    for fila in filas:
        celdas = [td.text.strip() for td in fila.find_elements(By.TAG_NAME, "td")]
        if len(celdas) == len(headers):
            datos.append(celdas)

    if not datos:
        return None

    df = pd.DataFrame(datos, columns=headers)
    df["Fecha"] = fecha_hoy

    return df

# GENERAR FECHAS

def fechas_ayer_y_hoyP():
    hoy = datetime.now()
    ayer = hoy - timedelta(days=1)

    return [
        ayer.strftime("%d/%m/%Y"),
        hoy.strftime("%d/%m/%Y")
    ]

# PROGRAMA PRINCIPAL

def main():
    csv_precios = "ArchBIP/precios_historico_emmsa.csv"

    # Fechas ya guardadas
    fechas_existentes = set()
    if os.path.exists(csv_precios):
        df_v = pd.read_csv(csv_precios)
        if "Fecha" in df_v.columns:
            fechas_existentes = set(df_v["Fecha"].astype(str))
    else:
        df_v = pd.DataFrame()

    driver = get_driver()
    nuevos_datos = []

    for fecha in fechas_ayer_y_hoyP():
        print(f"📅 Procesando {fecha}")

        if fecha in fechas_existentes:
            print(f"✔ {fecha} ya existe, se omite")
            continue

        df_vol_new = scraper_precios(driver, fecha)
        if df_vol_new is not None:
            nuevos_datos.append(df_vol_new)

    driver.quit()

    if nuevos_datos:
        df_final = pd.concat([df_v] + nuevos_datos, ignore_index=True)
        df_final.drop_duplicates().to_csv(csv_precios, index=False, encoding="utf-8-sig")
        print("💾 CSV volúmenes actualizado")
    else:
        print("ℹ No hubo nuevos datos")

if __name__ == "__main__":
    main()