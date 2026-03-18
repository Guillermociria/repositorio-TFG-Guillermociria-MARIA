# 1. Definimos los valores que queremos insertar
valores = {
    "nombre": "Alex",
    "codigo": "12345-ABC"
}

try:
    # 2. Leemos el archivo original
    with open('plantilla.txt', 'r', encoding='utf-8') as archivo:
        contenido = archivo.read()

    # 3. Sustituimos las llaves {etiqueta} por los valores del diccionario
    # El desempaquetado (**valores) busca las llaves que coincidan con los nombres en el texto
    texto_final = contenido.format(**valores)

    # 4. Mostramos el resultado o lo guardamos
    print("Texto procesado:\n", texto_final)
    
    with open('resultado.txt', 'w', encoding='utf-8') as salida:
        salida.write(texto_final)

except FileNotFoundError:
    print("¡Ups! No encontré el archivo 'plantilla.txt'.")
except KeyError as e:
    print(f"Error: El archivo pide {e}, pero no lo definiste en el diccionario.")