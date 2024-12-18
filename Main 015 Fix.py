from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException, ElementClickInterceptedException
import time
import csv
from configparser import ConfigParser

# Variables necesarias
config = ConfigParser()
config.read('config.ini')
s = Service(r"C:\Users\juana\Documents\Programming\Python\main 007 y 0015\msedgedriver.exe")
table_ids = ["titulosUniversitariosTable", "titulosEspecialidadTable", "titulosFPTable"]
filename = "data.csv"
first_iteration = True 
person_data = []
starting_page = int(config['options']['page'])

# Inicio del script
driver = webdriver.Edge(service=s)
driver.maximize_window()
wait = WebDriverWait(driver, 15)
driver.get("https://reps.sanidad.gob.es/reps-web/inicio.htm")

# Buscar y aplicar filtro
search = driver.find_element(By.ID, 'nombre_filtro')
search.send_keys(" ")
filtrBtn = driver.find_element(By.ID, 'filtro')
filtrBtn.click()
time.sleep(2)

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
    for _ in range(starting_page - 1):
        try:
            nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
            nextBtn.click()
        except TimeoutException:
            print("No se pudo avanzar a la página inicial definida. Continuando desde la actual.")
            break

# Iterar a través de las páginas
for i in range(starting_page, pages + 1):
    print(f"Procesando página {i} de {pages}...")
    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody/tr[1]/td').text != first_row_data
        )
    except TimeoutException:
        print("No se detectó cambio en los datos. Verificando siguiente página...")

    # Procesar filas de la tabla
    table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
    rows = table.find_elements(By.TAG_NAME, 'tr')

    for row in rows:
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

        # Guardar en CSV
        with open(filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(person_data)
        person_data.clear()

        btnClose = wait.until(EC.element_to_be_clickable((By.ID, 'headerButtonClose')))
        btnClose.click()

    # Avanzar a la siguiente página
    try:
        nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
        if 'disabled' in nextBtn.get_attribute('class'):
            print("No hay más páginas disponibles.")
            break
        nextBtn.click()
        time.sleep(2)
    except TimeoutException:
        print("No se pudo avanzar a la siguiente página. Cerrando...")
        break

# Finalizar
print("Proceso completado.")
driver.quit()

