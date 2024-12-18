from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
import re
from configparser import ConfigParser

# --- Variables Necesarias ---
config = ConfigParser()
config.read('config.ini')

# Path del driver
driver_service = Service(r"C:\\Users\\EduardoFigueiredo\\OneDrive\\Documentos\\_panel2009\\05. Servicios\\Python prg\\prg\\Extractor REPS\\REPS-main\\REPS-main\\msedgedriver.exe")

table_ids = ["titulosUniversitariosTable", "titulosEspecialidadTable", "titulosFPTable"]
data_filename = "data.csv"
person_data = []
starting_page = int(config['options'].get('page', 1))

# --- Configuración del Driver ---
driver = webdriver.Edge(service=driver_service)
driver.maximize_window()
wait = WebDriverWait(driver, 15)

# --- Navegación a la página principal ---
driver.get("https://reps.sanidad.gob.es/reps-web/inicio.htm")

# --- Filtro Inicial ---
search_box = driver.find_element(By.ID, 'nombre_filtro')
search_box.send_keys(" ")
filter_btn = driver.find_element(By.ID, 'filtro')
filter_btn.click()

def limpiar_numero_pagina(texto):
    """ Extrae solo el número de una cadena de texto. """
    numeros = re.findall(r'\d+', texto)
    return int(numeros[0]) if numeros else 0

# --- Obtención del Número Total de Páginas ---
time.sleep(2)
try:
    pagina_texto = driver.find_element(By.XPATH, '//*[@id="profesionalTable_paginate"]/ul/li[last()-1]/a').text
    total_pages = limpiar_numero_pagina(pagina_texto)
    print(f"Número total de páginas: {total_pages}")
except Exception as e:
    print(f"Error obteniendo el número total de páginas: {e}")
    driver.quit()
    exit()

# --- Avance a la Página Guardada ---
for _ in range(starting_page - 1):
    next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
    next_btn.click()

def guardar_progreso(pagina):
    config['options']['page'] = str(pagina)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def extraer_datos():
    global person_data
    for row in driver.find_elements(By.XPATH, '//*[@id="profesionalTable"]/tbody/tr'):
        try:
            # Clic en botón de detalle
            btnPerson = row.find_element(By.TAG_NAME, 'button')
            ActionChains(driver).move_to_element(btnPerson).click().perform()
            
            # Extracción de datos personales
            nombre = wait.until(EC.visibility_of_element_located((By.ID, 'nombreModal'))).text
            primer_apellido = wait.until(EC.visibility_of_element_located((By.ID, 'apellido1Modal'))).text
            try:
                segundo_apellido = wait.until(EC.visibility_of_element_located((By.ID, 'apellido2Modal'))).text
            except TimeoutException:
                segundo_apellido = ""
                print("Segundo apellido no encontrado.")

            nombre_completo = f"{nombre} {primer_apellido} {segundo_apellido}".title()
            person_data = [nombre_completo]

            # Extracción de datos académicos
            try:
                academic_tab = driver.find_element(By.XPATH, '//*[@id="pestanas"]/ul/li[2]')
                academic_tab.click()
                for table_id in table_ids:
                    try:
                        academic_table = driver.find_element(By.XPATH, f'//*[@id="{table_id}"]/tbody')
                        rows = academic_table.find_elements(By.TAG_NAME, 'tr')
                        for row in rows:
                            cols = row.find_elements(By.TAG_NAME, 'td')
                            person_data.extend([col.text for col in cols if col.text])
                    except Exception:
                        continue
            except TimeoutException:
                print("La pestaña de datos académicos no está disponible.")

            # Guardar en CSV
            with open(data_filename, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(person_data)
                print(f"Datos guardados: {person_data}")
            person_data.clear()

            # Cerrar modal
            close_btn = wait.until(EC.element_to_be_clickable((By.ID, 'headerButtonClose')))
            close_btn.click()
            wait.until(EC.invisibility_of_element_located((By.ID, 'headerButtonClose')))
        
        except (StaleElementReferenceException, ElementClickInterceptedException):
            print("Elemento stale detectado, reintentando...")
            driver.refresh()
            continue

# --- Iteración por Todas las Páginas ---
for current_page in range(starting_page, total_pages + 1):
    print(f"Procesando página {current_page} de {total_pages}...")
    extraer_datos()
    guardar_progreso(current_page)

    try:
        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
        next_btn.click()
        wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="profesionalTable"]/tbody/tr[1]')))
    except TimeoutException:
        print("No se pudo avanzar a la siguiente página. Deteniendo ejecución.")
        break

# --- Finalización del Script ---
print("Proceso completado.")
driver.quit()

