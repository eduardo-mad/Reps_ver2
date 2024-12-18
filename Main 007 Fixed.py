from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait  
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import time
import csv
from configparser import ConfigParser

#Required variables
#Reading the configuration in config.ini
config = ConfigParser()
config.read('config.ini')
s = Service(r"C:\Users\EduardoFigueiredo\OneDrive\Documentos\_panel2009\05. Servicios\Python prg\prg\Extractor REPS\REPS-main\REPS-main\msedgedriver.exe")
table_ids = ["titulosUniversitariosTable", "titulosEspecialidadTable", "titulosFPTable"]
filename = "data.csv"
first_iteration = True 
person_data = []
starting_page = int(config['options']['page']) # Cambiar a última pagina completada en caso de que el programa se cierre sin completarse

#Script starts
driver = webdriver.Edge(service=s)
driver.maximize_window()
wait = WebDriverWait(driver, 9)
driver.get("https://reps.sanidad.gob.es/reps-web/inicio.htm")
search = driver.find_element(By.ID, 'nombre_filtro')
search.send_keys(" ")
filtrBtn = driver.find_element(By.ID, 'filtro')
filtrBtn.click()
time.sleep(2)

table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
rows = table.find_elements(By.TAG_NAME, 'tr')
first_row_data = rows[0].find_element(By.TAG_NAME, 'td').text

pages = int(driver.find_element(By.XPATH, '//*[@id="profesionalTable_paginate"]/ul/li[9]/a').text)
if starting_page > 1:
    for i in range(starting_page):
        nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
        nextBtn.click()

WebDriverWait(driver, 6000).until(lambda driver: driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody/tr[1]/td').text != first_row_data) #Cambiar el número según sea necesario

for i in range(pages):
    page_number = starting_page
    table = driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody')
    rows = table.find_elements(By.TAG_NAME, 'tr')
    first_row_data = rows[0].find_element(By.TAG_NAME, 'td').text
    for row in rows:
        
        try:
            btnPerson = row.find_element(By.TAG_NAME, 'button')
            btnPerson.click()
        except StaleElementReferenceException:
            print("Elemento stale detectado, reintentando...")
            btnPerson = row.find_element(By.TAG_NAME, 'button')
            btnPerson.click()
               
        nombre = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, 'nombreModal'))
        )
        nombre = driver.find_element(By.ID, 'nombreModal').text

        nombre_completo = "" + nombre
        primer_apellido = wait.until(EC.visibility_of_element_located((By.ID, 'apellido1Modal'))).text
        nombre_completo = nombre_completo + " " + primer_apellido
        try:
            segundo_apellido = wait.until(EC.visibility_of_element_located((By.ID, 'apellido2Modal'))).text
        except TimeoutException:
            segundo_apellido = "" 
            print("Segundo apellido not found.")
        nombre_completo = nombre_completo + " " + segundo_apellido
        person_data.append(nombre_completo.title())
 
        try:
            academicData = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="pestanas"]/ul/li[2]')))
            academicData.click()
        except TimeoutException:
            print("The academicData tab is not visible or does not exist.")

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
                                    if(td.text != ""):
                                        #print(td.text)
                                        person_data.append(td.text)
                    except TimeoutException:
                        continue

        profData = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="pestanas"]/ul/li[3]')))
        profData.click()

        profTable = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="situacionProfesionalTable"]/tbody')))
        positions = profTable.find_elements(By.TAG_NAME, 'tr')
        
        for position in positions:
            position.click() 
            position_data = position.find_elements(By.TAG_NAME, 'td')
            for pd in position_data:
                person_data.append(pd.text.title())
            if first_iteration:
                centerBtn = driver.find_element(By.XPATH, '//*[@id="headingOne"]/h4/a')
                centerBtn.click()
                time.sleep(1)
                first_iteration = False
            centerTbl = driver.find_element(By.XPATH, '//*[@id="centroSituacionTable"]/tbody')
            centerData = centerTbl.find_elements(By.TAG_NAME, 'td')
            for cd in centerData:
                person_data.append(cd.text.title())

        btnClose = wait.until(EC.element_to_be_clickable((By.ID, 'headerButtonClose')))
        btnClose.click()
        #print(person_data)
        with open(filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(person_data)
        person_data.clear()
        wait.until(EC.invisibility_of_element((By.ID, 'headerButtonClose')))
    config['options']['page'] = str(page_number + i + 1)

    with open('config.ini', 'w') as configfile:
        config.write(configfile)

    nextBtn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="profesionalTable_next"]/a')))
    nextBtn.click()
    try:
        wait.until(lambda driver: driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody/tr[1]/td') and 
               driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody/tr[1]/td').text != first_row_data)
    except StaleElementReferenceException:
        print("Elemento stale detectado. Reintentando...")
        time.sleep(2)  # Espera breve antes de intentar nuevamente
        wait.until(lambda driver: driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody/tr[1]/td') and 
               driver.find_element(By.XPATH, '//*[@id="profesionalTable"]/tbody/tr[1]/td').text != first_row_data)


time.sleep(5)
driver.quit()
  