import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from supabase import Client, create_client
from models import Mascota, Cliente, Cita, Diagnostico, Funcionario, LoginRequest, CompleteCitaData
from datetime import date  # Opcional: si prefieres validar que sea una fecha

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Obtener las variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")  # Clave secreta para JWT
ALGORITHM = "HS256"  # Algoritmo para firmar el token JWT

# Crear el cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir solicitudes desde el frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2PasswordBearer será usado para proteger rutas con tokens JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Funciones de autenticación ---
def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # Devuelve el payload completo, incluyendo el rol
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# --- GET Methods ---
@app.get("/check-table/")
async def check_db(tabla: str):
    try:
        # si la tabla es clientes no debe de regresar la contraseña
        if tabla == "Clientes":
            response = supabase.table(tabla).select("id, nombre_usuario, correo").execute()
            return {"message": "Conectado a la base de datos", "data": response.data}
        else:
            response = supabase.table(tabla).select("*").execute()
            return {"message": "Conectado a la base de datos", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mascotas/")
async def get_mascotas():
    try:
        response = supabase.table("Mascotas").select("*").execute()
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/citas/{id}")
async def get_citas_mascota(id: int):
    try:
        response = supabase.table("Citas").select("*").eq("id_mascota", id).execute()
        print("DATA")
        print(response.data)
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/citas/")
async def get_citas():
    try:
        response = supabase.table("Citas").select("*").execute()
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/citas-veterinario/{id}")
async def get_citas_veterinario(id: int):
    try:
        response = supabase.table("Historial").select("*").eq("veterinario_id", id).execute()
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/veterinarios")
async def get_veterinarios():
    try:
        response = supabase.table("Funcionario").select("*").eq("puesto", "Veterinario").execute()
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/protected/")
async def protected_route(token: str = Depends(verify_token)):
    return {"message": "Acceso permitido", "email": token["sub"]}

@app.get("/reportes/")
async def get_reportes(token: dict = Depends(verify_token)):
    # Verifica que el rol del usuario sea 'admin' o 'assistant'
    if token.get("role") not in ['Administrador', 'Recepcionista']:
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a esta ruta")
    
    # Lógica para retornar los reportes
    return {"message": "Acceso a reportes permitido"}

@app.get("/citas/{id_cita}/fecha")
async def get_citas_fecha(id_cita: int):
    print(id_cita)
    try:
        response = supabase.table("Citas").select("*").eq("id", id_cita).execute()
        print(response.data)
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.delete("/citas/{id_cita}/cancelar")
async def cancelar_cita(id_cita: int):
    try:
        # Intentamos eliminar la cita con el id especificado
        response = supabase.table("Citas").delete().eq("id", id_cita).execute()
        
        # Verificamos si la operación fue exitosa
        if not response.data:  # Esto indica que no se encontró la cita
            raise HTTPException(status_code=404, detail="Cita no encontrada o no pudo ser cancelada")
        
        # Si todo salió bien, enviamos una respuesta de éxito
        return {"message": "Cita cancelada exitosamente", "data": response.data}
        
    except Exception as e:
        # Captura y muestra el error para identificar el problema exacto
        print(f"Error al intentar cancelar la cita: {e}")
        raise HTTPException(status_code=500, detail="Ocurrió un error al cancelar la cita.")

@app.get("/vacunas_mascotas/{id_mascota}")
async def get_vacunas_mascotas(id_mascota: int):
    try:
        response = supabase.from_("VacunasMascotas").select("*").filter("mascota", "eq", id_mascota).execute()
        print(response.data)
        return response.data
    except Exception as e:
        print("Data error")
        print("Exception:", e)
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/vacunas/{id_vacuna}")
async def get_vacunas(id_vacuna: int):
    try:
        response = supabase.table("Vacunas").select("*").eq("id", id_vacuna).execute()
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


#Método para obtener los resultados de un diagnóstico relacionado a un cliente 
@app.get("/historial/cliente/{id_mascota}")
async def get_historial(id_mascota: int):
    try:
        response = supabase.table("Historial").select("*").eq("id_mascota", id_mascota).execute()
        return {"data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/veterinarios/{id_veterinario}")
async def get_veterinarios(id_veterinario: int):
    try:
        query = (
            supabase.table("Funcionario")
            .select("*")
            .eq("puesto", "Veterinario")
            .eq("id", id_veterinario)
            .execute()
        )
        return {"data": query.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# --- POST Methods ---
@app.post("/mascotas/")
async def create_mascota(mascota: Mascota):
    try:
        response = supabase.table("Mascotas").insert(mascota.dict()).execute()
        return {"message": "Mascota creada", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clientes/")
async def create_cliente(cliente: Cliente):
    try:
        hashed_password = hash_password(cliente.contraseña)
        cliente_data = cliente.dict()
        cliente_data["contraseña"] = hashed_password
        response = supabase.table("Clientes").insert(cliente_data).execute()
        return {"message": "Cliente creado", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/citas/")
async def create_cita(cita: Cita):
    try:
        response = supabase.table("Citas").insert(cita.dict()).execute()
        return {"message": "Cita creada", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-mascota-image/{mascota_id}")
async def upload_mascota_image(mascota_id: int, file: UploadFile = File(...)):
    try:
        # Leer el archivo de manera segura
        file_data = await file.read()
        
        # Intentar subir el archivo
        file_path = f"mascotas/{mascota_id}/{file.filename}"
        response = supabase.storage.from_("images").upload(file_path, file_data)
        
        # Revisar el status code de la respuesta y el contenido para errores
        response_data = response.json()
        if response.status_code != 200 or "error" in response_data:
            error_message = response_data.get("error", {}).get("message", "Error desconocido")
            raise HTTPException(status_code=400, detail=f"Error al subir la imagen: {error_message}")

        # Generar URL pública
        image_url = supabase.storage.from_("images").get_public_url(file_path)

        # Actualizar URL en la base de datos
        supabase.table("Mascotas").update({"image_url": image_url}).eq("id", mascota_id).execute()

        return {"message": "Imagen subida correctamente", "image_url": image_url}
        
    except Exception as e:
        # Registrar el error exacto para depuración
        print(f"Error en upload_mascota_image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")

@app.post("/diagnosticos/")
async def create_diagnostico(diagnostico: Diagnostico):
    try:
        response = supabase.table("Diagnosticos").insert(diagnostico.dict()).execute()
        return {"message": "Diagnóstico creado", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/funcionarios/")
async def create_funcionario(funcionario: Funcionario):
    try:
        hashed_password = hash_password(funcionario.contraseña)
        funcionario_data = funcionario.dict()
        funcionario_data["contraseña"] = hashed_password
        response = supabase.table("Funcionario").insert(funcionario_data).execute()
        return {"message": "Funcionario creado", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login/")
async def login_user(login_data: LoginRequest):
    table = "Clientes" if login_data.role == "cliente" else "Funcionario"
    response = supabase.table(table).select("*").eq("correo", login_data.correo).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")

    user = response.data[0]
    if not verify_password(login_data.contraseña, user["contraseña"]):
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")

    # Generar token JWT con el rol del usuario
    print(user)
    if table == "Clientes":
        token = create_access_token(data={"sub": user["correo"], "role": "cliente", "nombre": user["nombre_usuario"], "client_id": user["id"]}, expires_delta=timedelta(minutes=30))
        return {"access_token": token, "token_type": "bearer"}
    token = create_access_token(data={"sub": user["correo"], "role": user["puesto"], "nombre": user["nombre"], "id": user["id"]}, expires_delta=timedelta(minutes=30))
    return {"access_token": token, "token_type": "bearer"}


@app.post("/verify-client/")
async def verify_client(correo: str, contraseña: str):
    try:
        # Buscar el cliente por correo en la base de datos
        response = supabase.table("Clientes").select("*").eq("correo", correo).execute()

        # Verificar si el cliente existe
        if len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        cliente = response.data[0]  # Obtener los datos del cliente
        hashed_password = cliente["contraseña"]  # La contraseña cifrada almacenada en la base de datos

        # Verificar si la contraseña es correcta
        if verify_password(contraseña, hashed_password):
            return {"message": "Contraseña correcta"}
        else:
            return {"message": "Contraseña incorrecta"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/citas/{id_cita}/completar")
async def completar_cita(id_cita: int, data: CompleteCitaData):
    try:
        # Obtenenemos la cita
        cita_response = supabase.table("Citas").select("*").eq("id", id_cita).execute()
        
        if not cita_response.data:
            raise HTTPException(status_code=404, detail="Cita no encontrada")

        cita = cita_response.data[0]

        # Preparar datos para insertar en Historial usando los datos proporcionados
        historial_data = {
            "id_mascota": cita["id_mascota"],
            "fecha": cita["fecha_cita"],
            "tipo": data.tipo,
            "descripcion": data.motivo,
            "veterinario_id": cita["id_veterinario"],
            "resultado": data.resultado
        }

        # Insertar la cita en el historial
        historial_response = supabase.table("Historial").insert(historial_data).execute()
        
        if not historial_response.data:
            raise HTTPException(status_code=500, detail="No se pudo registrar la cita en el historial")

        # Eliminar la cita de la tabla de citas
        delete_response = supabase.table("Citas").delete().eq("id", id_cita).execute()
        
        if not delete_response.data:
            raise HTTPException(status_code=500, detail="No se pudo eliminar la cita de la tabla de citas")

        return {"message": "Cita completada y movida al historial exitosamente"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error: {str(e)}")
    
#
# Ejemplo de una ruta protegida
@app.get("/protected/")
async def protected_route(token: str = Depends(verify_token)):
    return {"message": "Acceso permitido", "email": token["sub"]}


@app.put("/mascotas/{id}/editar")
async def update_mascota(id: int, mascota: Mascota):
    try:
        response = supabase.table("Mascotas").update(mascota.dict()).eq("id", id).execute()
        return {"message": "Mascota actualizada", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))