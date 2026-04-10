import json
import random
import string
import requests


def generar_placa(patron):
    """Genera una placa aleatoria basada en un patrón como 'CCC-NNN-C'"""
    resultado = ""
    for char in patron:
        if char == 'C': # Letra Mayúscula
            resultado += random.choice(string.ascii_uppercase)
        elif char == 'c': # Letra minúscula
            resultado += random.choice(string.ascii_lowercase)
        elif char == 'N': # Número
            resultado += random.choice(string.digits)
        else: # Mantiene guiones o espacios
            resultado += char
    return resultado

def crear_prompt_robusto(con_placa=False):
    # 1. Configuración de Patrones (puedes agregar más de 15 aquí)
    patrones = ["CCC-NNN-C", "NNN-CCC", "CC-NN-CC", "NNNN-CCC", "C-NNNNN", "CCC-NNN"]
    
    # 2. Listas de Variedad
    paises = ["Mexican", "American", "Spanish", "German", "Japanese", "Brazilian", "French"]
    
    estilos_fondo = [
        "dark license plate with black background and white letters, minimalistic design, clean and modern",
        "classic white background plate with black high contrast letters, icons decal and painting details",
        "vintage yellow plate with black embossed characters",
        "modern blue gradient plate with white reflective text, subtle texture, slight wear and tear"
    ]
    
    niveles_danos = [
        "pristine condition, brand new, shiny", # Nada de daño
        "slightly used, minor scratches, some dust", # Poco daño
        "heavily damaged, broken corners, rusted metal, illegible parts, extreme wear", # Muy dañado
        "weathered, sun-faded colors, covered in dried mud" # Daño medio/sucio
    ]

    # 3. Selección Aleatoria
    pais = random.choice(paises)
    placa = generar_placa(random.choice(patrones))
    fondo = random.choice(estilos_fondo)
    dano = random.choice(niveles_danos)
    
    # 4. Ensamblaje del Prompt
    prompt_final = (f"photo of a {pais} licence plate with the numbers: {placa} in a car. "
                    f"{fondo}, {dano}, high resolution, detailed texture.")
    
    if con_placa:
        return prompt_final, placa
    return prompt_final


def normalizar_nombre_archivo(nombre):
    caracteres_validos = string.ascii_letters + string.digits + "-_"
    limpio = "".join(c for c in nombre if c in caracteres_validos)
    return limpio if limpio else "imagen"


def construir_filename_prefix(directorio_salida, nombre_base):
    base = normalizar_nombre_archivo(nombre_base)
    directorio = directorio_salida.strip().replace("\\", "/").strip("/")
    if directorio:
        return f"{directorio}/{base}"
    return base

# Configuración
COMFYUI_URL = "http://127.0.0.1:8188/prompt"

# El JSON que me pasaste (simplificado para el script)
workflow_data = {
    "64": {"inputs": {"filename_prefix": "DamageOK1", "images": ["65", 0]}, "class_type": "SaveImage"},
    "65": {"inputs": {"samples": ["72", 0], "vae": ["68", 0]}, "class_type": "VAEDecode"},
    "66": {"inputs": {"text": "PROMPT_A_REEMPLAZAR", "clip": ["70", 0]}, "class_type": "CLIPTextEncode"},
    "67": {"inputs": {"width": 768, "height": 512, "batch_size": 1}, "class_type": "EmptySD3LatentImage"},
    "68": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"},
    "69": {"inputs": {"unet_name": "z_image_turbo_nvfp4.safetensors", "weight_dtype": "default"}, "class_type": "UNETLoader"},
    "70": {"inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2", "device": "default"}, "class_type": "CLIPLoader"},
    "71": {"inputs": {"conditioning": ["66", 0]}, "class_type": "ConditioningZeroOut"},
    "72": {"inputs": {"seed": 0, "steps": 5, "cfg": 1, "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 0.8, "model": ["73", 0], "positive": ["66", 0], "negative": ["71", 0], "latent_image": ["67", 0]}, "class_type": "KSampler"},
    "73": {"inputs": {"shift": 3, "model": ["69", 0]}, "class_type": "ModelSamplingAuraFlow"}
}

def generar_imagen(prompt_texto, nombre_archivo_base, directorio_salida=""):
    # 1. Modificar el texto en el nodo 66
    workflow_data["66"]["inputs"]["text"] = prompt_texto

    # 1.1 Nombre/ubicación de salida en el nodo SaveImage (64)
    workflow_data["64"]["inputs"]["filename_prefix"] = construir_filename_prefix(
        directorio_salida,
        nombre_archivo_base,
    )
    
    # 2. Modificar la semilla en el nodo 72 para que la imagen sea distinta cada vez
    workflow_data["72"]["inputs"]["seed"] = random.randint(1, 1000000000000)

    # 2.1 Steps aleatorios entre 1 y 5
    workflow_data["72"]["inputs"]["steps"] = random.randint(1, 5)

    # 2.2 Resolucion aleatoria entre 512x512 y 768x512
    ancho, alto = random.choice([(512, 512), (768, 512)])
    workflow_data["67"]["inputs"]["width"] = ancho
    workflow_data["67"]["inputs"]["height"] = alto
    print(
        f"Parámetros: steps={workflow_data['72']['inputs']['steps']} | resolución={ancho}x{alto}"
    )

    # 3. Enviar la petición
    payload = {"prompt": workflow_data}
    try:
        response = requests.post(COMFYUI_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        prompt_id = data.get("prompt_id", "sin_id")
        print(f"Éxito: Generación en cola. ID: {prompt_id}")
    except requests.RequestException as e:
        print(f"Error de conexión con ComfyUI: {e}")
    except ValueError:
        print(f"Respuesta no válida de ComfyUI: {response.text}")


# --- INTEGRACIÓN FUNCIÓN DE COMFYUI ---

def ejecutar_iteraciones(cantidad, directorio_salida=""):
    for i in range(cantidad):
        nuevo_prompt, placa = crear_prompt_robusto(con_placa=True)
        print(f"\nEncolando {i+1}/{cantidad}...")
        print(f"Prompt: {nuevo_prompt}")
        print(f"Archivo base: {placa}")
        
        generar_imagen(nuevo_prompt, placa, directorio_salida)

if __name__ == "__main__":
    try:
        cantidad = int(input("¿Cuántas imágenes quieres encolar en ComfyUI?: ").strip())
    except ValueError:
        print("Cantidad inválida. Debe ser un número entero.")
    else:
        if cantidad <= 0:
            print("La cantidad debe ser mayor a 0.")
        else:
            directorio = input(
                "Directorio de salida dentro de ComfyUI/output (vacío para raíz): "
            ).strip()
            ejecutar_iteraciones(cantidad, directorio)








