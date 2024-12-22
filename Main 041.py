# Importación de bibliotecas necesarias
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.edge.options import Options
from datetime import datetime
import csv
from configparser import ConfigParser
import os

# Configuración del archivo de configuración para parámetros de ejecución
config = ConfigParser()
config_path = os.path.abspath('config.ini')  # Ruta absoluta del archivo de configuración
config.read(config_path)

# Configuración del servicio y variables iniciales
s = Service(r"C:\Users\EduardoFigueiredo\OneDrive\Documentos\_panel2009\05. Servicios\Python prg\prg\Extractor REPS\REPS-main\REPS-main\msedgedriver.exe")
table_ids = ["titulosUniversitariosTable", "titulosEspecialidadTable", "titulosFPTable"]  # IDs de tablas académicas
filename = "data.csv"  # Archivo de salida
first_iteration = True
person_data = []  # Lista para almacenar datos extraídos temporalmente
starting_page = int(config['options']['page'])  # Página inicial configurada en config.ini

# Configuración del navegador
options = Options()
#options.add_argument('--headless=new')  # Opcional: ejecutar en modo headless
driver = webdriver.Edge(service=s, options=options)
driver.maximize_window()
wait = WebDriverWait(driver, 15)

# Abrir la URL objetivo
driver.get("https://reps.sanidad.gob.es/reps-web/inicio.htm")

# Buscar y aplicar el filtro en la página principal
search = driver.find_element(By.ID, 'nombre_filtro')  # Campo de búsqueda
search.send_keys(" ")  # Enviar un espacio para activar el filtro
filtrBtn = driver.find_element(By.ID, 'filtro')  # Botón de aplicar filtro
filtrBtn.click()

# Esperar hasta que se carguen al menos 5 filas en la tabla de resultados
wait.until(lambda driver: len(driver.find_elements(By.XPATH, "//table[@id='profesionalTable']/tbody/tr")) >= 5)

# Verificar la tabla principal de resultados
try:
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="profesionalTable"]/tbody')))
except TimeoutException:
    print("No se pudo cargar la tabla principal. Cerrando...")
    driver.quit()
    exit()

# Obtener filas iniciales de la tabla
table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
rows = table.find_elements(By.TAG_NAME, 'tr')
first_row_data = rows[0].find_element(By.TAG_NAME, 'td').text

# Manejo de paginación en la tabla de resultados
try:
    pagination_elements = driver.find_elements(By.XPATH, '//*[@id="profesionalTable_paginate"]/ul/li/a')
    pages = 1  # Número de páginas a procesar
    for element in pagination_elements:
        text = element.text.strip()
        if text.isdigit():
            pages = max(pages, int(text))
except NoSuchElementException:
    print("No se encontró paginador. Asumiendo una sola página.")
    pages = 1

# Saltar a la página inicial configurada
if starting_page > 1:
    n = 0
    while n < starting_page - 1:
        try:
            if (starting_page - n > 25):  # Moverse por bloques de 25 páginas si es necesario
                for i in range(25):
                    print(f"En página {n + 1} de {starting_page}")
                    nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
                    nextBtn.click()
                    n += 1
            else:  # Avanzar página a página
                print(f"En página {n + 1} de {starting_page}")
                nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
                nextBtn.click()
                n += 1

            # Esperar cambio en la primera fila de la tabla
            wait.until(lambda driver: driver.execute_script(
                "return document.querySelector('#profesionalTable tbody tr:first-child td').textContent.trim()") != first_row_data)
            print("Cargando...")
            first_row_data = driver.execute_script(
                "return document.querySelector('#profesionalTable tbody tr:first-child td').textContent.trim()")
        except TimeoutException:
            print("No se pudo avanzar a la página inicial definida. Continuando desde la actual.")
            break

# Iterar a través de las páginas para extraer datos
for i in range(starting_page, pages + 1):
    print(f"Procesando página {i} de {pages}...")
    print("Hora en la que se inicia la extracción: " + datetime.now().strftime('%H:%M:%S'))

    # Procesar filas de la tabla en la página actual
    table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
    rows = table.find_elements(By.TAG_NAME, 'tr')

    for index, row in enumerate(rows):
        print("Extrayendo datos de índice: " + str(index + 1))
        # Manejo de botones para abrir modales
        try:
            btnPerson = row.find_element(By.TAG_NAME, 'button')
            try:
                btnPerson.click()
            except ElementClickInterceptedException:
                actions = ActionChains(driver)
                actions.move_to_element(btnPerson).click().perform()
        except StaleElementReferenceException:
            print("Elemento stale detectado, reintentando...")
            btnPerson = row.find_element(By.TAG_NAME, 'button')
            btnPerson.click()

        # Extraer datos del modal
        try:
            nombre = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.ID, 'nombreModal'))).text
        except TimeoutException:
            print("No se pudo obtener el nombre. Continuando...")
            continue

        # Procesar datos adicionales del modal
        nombre_completo = nombre
        try:
            primer_apellido = wait.until(EC.visibility_of_element_located((By.ID, 'apellido1Modal'))).text
        except TimeoutException:
            primer_apellido = ""
        try:
            segundo_apellido = wait.until(EC.visibility_of_element_located((By.ID, 'apellido2Modal'))).text
        except TimeoutException:
            segundo_apellido = ""

        nombre_completo = f"{nombre} {primer_apellido} {segundo_apellido}".strip()
        person_data.append(nombre_completo)

        # Procesar datos académicos
        try:
            academicData = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="pestanas"]/ul/li[2]')))
            academicData.click()
        except TimeoutException:
            print("No se pudo acceder a la pestaña de datos académicos.")
            continue

        # Navegar por las tablas académicas y extraer datos
        tabs_ul = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="pestanasTitulaciones"]/ul')))
        tab_items = tabs_ul.find_elements(By.TAG_NAME, 'li')
        for tab in tab_items:
            if tab.is_displayed():
                tab.click()
                for table_id in table_ids:
                    try:
                        academicTable = wait.until(EC.presence_of_element_located(
                            (By.XPATH, f'//*[@id="{table_id}"]/tbody')))
                        titles = academicTable.find_elements(By.TAG_NAME, 'tr')
                        for title in titles:
                            title_data = title.find_elements(By.TAG_NAME, 'td')
                            for td in title_data:
                                if td.text != "":
                                    person_data.append(td.text)
                    except TimeoutException:
                        continue

        # Procesar datos profesionales
        try:
            profData = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pestanas"]/ul/li[3]')))
            profData.click()
        except TimeoutException:
            print("No se pudo acceder a la pestaña de datos profesionales.")
            continue

        profTable = wait.until(EC.visibility_of_element_located(
            (By.XPATH, '//*[@id="situacionProfesionalTable"]/tbody')))
        positions = profTable.find_elements(By.TAG_NAME, 'tr')
        for position in positions:
            position.click()
            position_data = position.find_elements(By.TAG_NAME, 'td')
            for pd in position_data:
                person_data.append(pd.text.title())
            if first_iteration:
                centerBtn = driver.find_element(By.XPATH, '//*[@id="headingOne"]/h4/a')
                centerBtn.click()
                wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@id='datosSituacionProfesional']")))
                first_iteration = False
            centerTbl = driver.find_element(By.XPATH, '//*[@id="centroSituacionTable"]/tbody')
            centerData = centerTbl.find_elements(By.TAG_NAME, 'td')
            for cd in centerData:
                person_data.append(cd.text.title())

        # Guardar los datos extraídos en un archivo CSV
        with open(filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(person_data)
        person_data.clear()

        # Cerrar el modal
        btnClose = wait.until(EC.element_to_be_clickable((By.ID, 'headerButtonClose')))
        btnClose.click()

    # Avanzar a la siguiente página
    try:
        current_page += 1
        config['options']['page'] = str(current_page)
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
        if 'disabled' in nextBtn.get_attribute('class'):
            print("No hay más páginas disponibles.")
            break
        nextBtn.click()
    except TimeoutException:
        print("No se pudo avanzar a la siguiente página. Cerrando...")
        break

# Finalizar el proceso
print("Proceso completado.")
driver.quit()
