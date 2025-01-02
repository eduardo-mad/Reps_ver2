from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.edge.options import Options
from datetime import datetime
import time
import csv
from configparser import ConfigParser
import os

# Variables necesarias
config = ConfigParser()
config_path = os.path.abspath('config.ini')  # Ensure the config file path is absolute
config.read(config_path)
s = Service(r"C:\Users\EduardoFigueiredo\OneDrive\Documentos\_panel2009\05. Servicios\Python prg\prg\Extractor REPS\REPS-main\REPS-main\msedgedriver.exe")
table_ids = ["titulosUniversitariosTable", "titulosEspecialidadTable", "titulosFPTable"]
filename = "data.csv"
first_iteration = True 
person_data = []
starting_page = int(config['options']['page'])

# Inicio del script
options = Options()
driver = webdriver.Edge(service=s, options=options)
driver.maximize_window()
wait = WebDriverWait(driver, 15)
driver.get("https://reps.sanidad.gob.es/reps-web/inicio.htm")

# Buscar y aplicar filtro
search = driver.find_element(By.ID, 'nombre_filtro')
search.send_keys(" ")
filtrBtn = driver.find_element(By.ID, 'filtro')
filtrBtn.click()
wait.until(
    lambda driver: len(driver.find_elements(By.XPATH, "//table[@id='profesionalTable']/tbody/tr")) >= 5
)

# Verificar la tabla de resultados
try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="profesionalTable"]/tbody'))
    )
except TimeoutException:
    print("No se pudo cargar la tabla principal. Cerrando...")
    driver.quit()
    exit()

table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
rows = table.find_elements(By.TAG_NAME, 'tr')
first_row_data = rows[0].find_element(By.TAG_NAME, 'td').text

# Manejo de paginación
try:
    pagination_elements = driver.find_elements(By.XPATH, '//*[@id="profesionalTable_paginate"]/ul/li/a')
    pages = 1
    for element in pagination_elements:
        text = element.text.strip()
        if text.isdigit():
            pages = max(pages, int(text))
except NoSuchElementException:
    print("No se encontró paginador. Asumiendo una sola página.")
    pages = 1

# Saltar a la página inicial definida en config.ini
if starting_page > 1:
    n = 0
    max_retries = 5
    while n < starting_page - 1:
        retries = 0
        while retries < max_retries:
            try:
                batch_end = min(starting_page - n, 25)
                for _ in range(batch_end):
                    nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
                    nextBtn.click()
                    n += 1

                wait.until(lambda driver: 
                    driver.execute_script(
                        "return document.querySelector('#profesionalTable tbody tr:first-child td').textContent.trim()") 
                    != first_row_data
                )
                first_row_data = driver.execute_script(
                    "return document.querySelector('#profesionalTable tbody tr:first-child td').textContent.trim()")
                print(f"En página {n} de {starting_page}")
                break
            except TimeoutException:
                retries += 1
                print(f"Intento {retries}/{max_retries} fallido al avanzar páginas. Reintentando...")
                if retries == max_retries:
                    print("No se pudo avanzar a la página inicial definida. Continuando desde la actual.")
                    break
                time.sleep(5)
        else:
            break

current_page = starting_page
for i in range(starting_page, pages + 1):
    print(f"Procesando página {i} de {pages}...")
    print("Hora en la que se inicia la extracción: " + datetime.now().strftime('%H:%M:%S'))

    table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
    rows = table.find_elements(By.TAG_NAME, 'tr')
    first_row_data = driver.execute_script(
        "return document.querySelector('#profesionalTable tbody tr:first-child td').textContent.trim()")

    for index, row in enumerate(rows):
        print("Extrayendo datos de índice: " + str(index + 1))
        attempt = 0
        while attempt < 3:
            try:
                btnPerson = row.find_element(By.TAG_NAME, 'button')
                btnPerson.click()
                break
            except ElementClickInterceptedException:
                actions = ActionChains(driver)
                actions.move_to_element(btnPerson).click().perform()
                break
            except StaleElementReferenceException:
                print(f"Elemento stale detectado, reintentando... Intento {attempt + 1}")
                table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
                rows = table.find_elements(By.TAG_NAME, 'tr')
                row = rows[index]
                attempt += 1
            except TimeoutException:
                print("Timeout al intentar interactuar con el botón. Continuando con la siguiente fila.")
                break
        else:
            print("No se pudo interactuar con el botón después de varios intentos. Continuando con la siguiente fila.")
            continue

        try:
            nombre = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.ID, 'nombreModal'))
            ).text
        except TimeoutException:
            print("No se pudo obtener el nombre. Continuando...")
            continue

        nombre_completo = nombre
        try:
            primer_apellido = wait.until(
                EC.visibility_of_element_located((By.ID, 'apellido1Modal'))
            ).text
        except TimeoutException:
            primer_apellido = ""

        try:
            segundo_apellido = wait.until(
                EC.visibility_of_element_located((By.ID, 'apellido2Modal'))
            ).text
        except TimeoutException:
            segundo_apellido = ""

        nombre_completo = f"{nombre} {primer_apellido} {segundo_apellido}".strip()
        person_data.append(nombre_completo)

        try:
            academicData = wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="pestanas"]/ul/li[2]'))
            )
            print(f"academicData size: {academicData.size}, displayed: {academicData.is_displayed()}")
            
            driver.execute_script("arguments[0].scrollIntoView(true);", academicData)
            time.sleep(1)
            
            academicData = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="pestanas"]/ul/li[2]'))
            )
            academicData.click()
        except TimeoutException:
            print("The academicData tab is not clickable or visible within the timeout period.")
        except ElementNotInteractableException:
            print("The academicData tab is not interactable. Attempting JavaScript click...")
            driver.execute_script("arguments[0].click();", academicData)
        except Exception as e:
            print(f"An unexpected error occurred with academicData: {str(e)}")

        tabs_ul = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="pestanasTitulaciones"]/ul')))
        tab_items = tabs_ul.find_elements(By.TAG_NAME, 'li')

        for tab in tab_items:
            if tab.is_displayed():
                tab.click()
                for table_id in table_ids:
                    try:
                        academicTable = wait.until(EC.presence_of_element_located((By.XPATH, f'//*[@id="{table_id}"]/tbody')))
                        titles = academicTable.find_elements(By.TAG_NAME, 'tr')
                        for title in titles:
                            title_data = title.find_elements(By.TAG_NAME, 'td')
                            for td in title_data:
                                if td.text != "":
                                    person_data.append(td.text)
                    except TimeoutException:
                        continue

        profData = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pestanas"]/ul/li[3]')))
        profData.click()

        profTable = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="situacionProfesionalTable"]/tbody')))
        positions = profTable.find_elements(By.TAG_NAME, 'tr')

        for attempt in range(3):
            try:
                for position in positions:
                    positions = profTable.find_elements(By.TAG_NAME, 'tr')
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
                break
            except StaleElementReferenceException:
                print(f"Elemento stale detectado al procesar posiciones. Reintentando... Intento {attempt + 1}")
                time.sleep(2)

        with open(filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(person_data)
        person_data.clear()

        btnClose = wait.until(EC.element_to_be_clickable((By.ID, 'headerButtonClose')))
        btnClose.click()

    try:
        current_page += 1
        config['options']['page'] = str(current_page)
        with open(config_path, 'w') as configfile:
            config.write(configfile)

        for attempt in range(3):
            try:
                nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
                if 'disabled' in nextBtn.get_attribute('class'):
                    print("No hay más páginas disponibles.")
                    break
                nextBtn.click()
                wait.until(lambda driver: 
                    driver.execute_script(
                        "return document.querySelector('#profesionalTable tbody tr:first-child td').textContent.trim()"
                    ) != first_row_data
                )
                print(f"En página {current_page} de {pages}")
                break
            except TimeoutException:
                print(f"Timeout al avanzar a la página. Reintentando... ({attempt + 1}/3)")
            except ElementClickInterceptedException:
                print("Modal intercept detected. Cerrando modal y reintentando...")
                try:
                    modal_close_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'close')))
                    modal_close_btn.click()
                except TimeoutException:
                    print("No se pudo cerrar el modal. Reintentando...")
            if attempt == 2:
                print("No se pudo avanzar a la siguiente página después de varios intentos. Continuando...")
                break

    except Exception as e:
        print(f"Error inesperado al avanzar a la siguiente página: {str(e)}. Continuando...")

print("Proceso completado.")
driver.quit()
