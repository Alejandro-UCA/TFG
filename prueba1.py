import requests
import pandas as pd
import io
from bs4 import BeautifulSoup
import time
import random

def extraccion_universidades():
    print("Inicializando proceso de extraccion")
    # Primero, obtener el xls de todas las universidades que existen en España
    universidades = "https://www.educacion.gob.es/ruct/listauniversidades?actual=universidades&cccaa=&tipo_univ=&d-8320336-e=2&6578706f7274=1&codigoUniversidad=&consulta=1"
    response = requests.get(universidades)

    #Panda no sabe leer Bytes, eso lo transforma en un archivo temporal en memoria en vez de guardarlo en disco
    archivo_en_memoria = io.BytesIO(response.content)
    df = pd.read_excel(archivo_en_memoria)
    df = df.fillna('Desconocido')
   
    df.to_json('datos/universidades.json', orient='records', force_ascii=False, indent=4)
    
    print("Universidades JSON creado. Pasamos a titulaciones.")

    #Enlazamos a la funcion para que extraiga las titulaciones de cada universidad
    codigos_universidad = df['Código'].tolist()
    extraccion_titulaciones_universidad(codigos_universidad)


def extraccion_titulaciones_universidad(codigos_universidades):
    urlBase = "https://www.educacion.gob.es/ruct/listaestudiosuniversidad?actual=universidades&d-1335801-e=2&6578706f7274=1&codigoUniversidad="
    for codigo in codigos_universidades:
        if int(codigo) < 10:
            url = urlBase + '00' + str(codigo)
        elif int(codigo) < 100:
            url = urlBase + '0' + str(codigo)
        else:
            url = urlBase + str(codigo)
        
        response = requests.get(url)
        archivo_en_memoria = io.BytesIO(response.content)
        df = pd.read_excel(archivo_en_memoria)
        df = df.fillna('Desconocido')
        
        df.to_json(f'datos/titulaciones_{codigo}.json', orient='records', force_ascii=False, indent=4)

        #No quiero que haga titulaciones que ya no existen, que en sus datos se denominan titulaciones extinguidas
        codigos_titulaciones_de_universidad = []

        for index, row in df.iterrows():
            if row['Detalle'] is not None and 'TITULACIÓN EXTINGUIDA' not in row['Detalle']:
                codigos_titulaciones_de_universidad.append(row['Código'])
        
        extraccion_informacion_titulacion(codigos_titulaciones_de_universidad, codigo)

        print("Universidad JSON creada "+ str(codigo))
    
    print("Universidades JSON creadas.")

def extraccion_informacion_titulacion(codigos_titulaciones, codigo_universidad):
    for codigo_titulacion in codigos_titulaciones:
        print(f"Extrayendo información de la titulación {codigo_titulacion} de la universidad {codigo_universidad}")
        #Esto ya no es un xls, es una web normal y no hay mas remedio que extraer la informacion del html
        urlExtraccion = f"https://www.educacion.gob.es/ruct/estudiouniversidad.action?codigoCiclo=SC&codigoEstudio={codigo_titulacion}&actual=universidad"
        response = requests.get(urlExtraccion)

        #Primera version, nos quedamos con todo el html
        if 'text/html' in response.headers.get('Content-Type', ''):
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')

            #Esto es algo complicado, pero para navegar por el HTML hay que intentar entender como esta hecho
            #Esto parece ser, de momento, lo normal en como la aplicacion lo estructura

            # Inicializamos la variable por si acaso no encontramos ninguno de los dos
            enlace_final = None 

            # 1. Primero buscamos el fieldset de "Correcciones" (como hacías tú)
            legend_correcciones = soup.find('legend', string=lambda text: text and "Correcciones" in text)

            if legend_correcciones:
            # Si existe, subimos al fieldset padre y buscamos el primer enlace
                fieldset = legend_correcciones.find_parent('fieldset')
                enlace_final = fieldset.find('a', href=True)

            # 2. Si NO hubo correcciones, buscamos el enlace del Plan de Estudios
            if not enlace_final:
            # Buscamos directamente la etiqueta label que tiene for="f_plan"
                label_plan = soup.find('label', attrs={'for': 'f_plan'})
                if label_plan:
                # Como el enlace está dentro de ese label, lo buscamos directamente
                    enlace_final = label_plan.find('a', href=True)
            
            if enlace_final is not None:
                try:
                    print(f"Encontrado enlace para descargar el BOE: {enlace_final['href']}")
                    href = enlace_final['href']
                    #Es un pdf, lo descargamos y guardamos
                    response = requests.get(href)
                    if response.status_code == 200:
                        nombre_pdf = href.split('/')[-1]
                        with open(f"datos/{nombre_pdf}_{codigo_titulacion}_{codigo_universidad}.pdf", 'wb') as pdf_file:
                            pdf_file.write(response.content)
                except Exception as e:
                    print("Error con uno de los pdfs BOE. Continuamos con el siguiente.")
                    continue

            with open(f"datos/titulacion_{codigo_titulacion}_{codigo_universidad}.html", 'w', encoding='utf-8') as f:
                f.write(html)
    
        #Obligamos a cada peticion esperarse
        time.sleep(random.uniform(8, 15))

if __name__ == "__main__":
    extraccion_universidades()