# Guía del proyecto: Pasaporte Digital de Producto en Odoo

Esta guía está pensada para alguien que **nunca ha usado Odoo** y sabe algo de Python.
Léela en orden: primero lo pones en marcha, luego entiendes cómo funciona y por último lo amplías.

---

## 1. Qué hace el módulo

Cada producto puede tener un **pasaporte digital**:

1. Indicas de qué está hecho (materiales, peso, % reciclado, país de origen).
2. Odoo calcula la **huella de carbono** (kg CO2e): materiales + fabricación + transporte.
3. Calcula indicadores de **circularidad**: % reciclable, % de contenido reciclado y una nota de A a E.
4. Genera un **código QR**. Quien lo escanee ve una página pública con toda la información, sin iniciar sesión.
5. Puedes imprimir una **etiqueta PDF** con el QR y también hay una versión **JSON** para máquinas.

Esto conecta con el Reglamento europeo de Ecodiseño (ESPR), que hará obligatorio el pasaporte digital
para baterías, textil, electrónica y otros productos en los próximos años.

> Los factores de emisión que vienen incluidos son **valores aproximados para aprender**, no datos oficiales.
> Para un uso real se sacan de bases como ecoinvent, DEFRA o ADEME.

---

## 2. Ponerlo en marcha (Windows)

### 2.1 Instalar Docker Desktop
Docker permite ejecutar Odoo y su base de datos sin instalarlos directamente en tu PC.

1. Descárgalo de https://www.docker.com/products/docker-desktop/ e instálalo (acepta activar WSL 2 si lo pide).
2. Reinicia el PC y abre Docker Desktop. Espera a que diga "Engine running".

### 2.2 Arrancar Odoo
Abre una terminal en la carpeta del proyecto (donde está `docker-compose.yml`) y ejecuta:

```bash
docker compose up -d
```

La primera vez tarda unos minutos porque descarga Odoo 18 y PostgreSQL.

### 2.3 Crear la base de datos
> También puedes crearla con un solo comando: `docker compose run --rm odoo odoo -d dpp -i product_digital_passport --stop-after-init`

1. Abre http://localhost:8069
2. Rellena el formulario:
   - **Master password:** `cambia-esta-clave` (está en `config/odoo.conf`)
   - **Database name:** `dpp` (tiene que ser exactamente este nombre; ver nota abajo)
   - Email y contraseña: los que quieras, serán tu usuario administrador
   - Marca **Demo data** para tener productos de ejemplo
3. Pulsa *Create database*.

> ¿Por qué `dpp`? Las páginas públicas del pasaporte se abren sin iniciar sesión, así que Odoo necesita saber
> qué base de datos usar. En `config/odoo.conf` está `dbfilter = ^dpp$`.

### 2.4 Instalar el módulo
1. Ve a **Apps**, quita el filtro "Apps" del buscador y busca `Digital Passport`.
2. Pulsa **Activate / Install**.
3. Aparecerá la app **Digital Passport** en el menú principal.

### 2.5 Probarlo
1. Abre *Digital Passport → Passports* y entra en **Electric City Bike**.
2. Ve a la pestaña **Digital Passport**: verás los materiales, la huella y el QR.
3. Pulsa **Open public page** para ver lo que vería un cliente.
4. Cambia un peso o un % reciclado y observa cómo se recalcula todo.
5. Arriba, en el icono de engranaje → **Print → Passport Label (QR)**, descarga la etiqueta.

**Para escanear el QR con el móvil:** el QR apunta a `localhost`, que en tu móvil no existe.
Activa el modo desarrollador (Ajustes → *Activate the developer mode*), ve a *Ajustes → Técnico → Parámetros del sistema*
y cambia `web.base.url` por la IP de tu PC, por ejemplo `http://192.168.1.50:8069`. El móvil debe estar en la misma wifi.

### 2.6 Cuando cambies el código
- Cambios en **Python**: reinicia Odoo con `docker compose restart odoo`.
- Cambios en **XML** (vistas, datos) o campos nuevos: además, actualiza el módulo:

```bash
docker compose run --rm odoo odoo -d dpp -u product_digital_passport --stop-after-init
```

```bash
docker compose restart odoo
```

### 2.7 Ejecutar los tests
Crean una base de datos aparte (`dpp_test`) y comprueban que los cálculos y la página pública funcionan:

```bash
docker compose run --rm odoo odoo -d dpp_test -i product_digital_passport --test-enable --test-tags /product_digital_passport --stop-after-init --db-filter=^dpp_test$
```

Al final del log busca `0 failed, 0 error(s)`. Para repetirlos desde cero, borra antes esa base de datos
desde http://localhost:8069/web/database/manager

---

## 3. Cómo funciona Odoo (explicado con tu código)

Odoo es un conjunto de **módulos** (Ventas, Inventario, Contabilidad…). Tú has creado uno más.
Todo módulo tiene la misma estructura:

```
addons/product_digital_passport/
├── __manifest__.py        ← "DNI" del módulo: nombre, dependencias y qué archivos cargar
├── __init__.py            ← importa las carpetas de Python
├── models/                ← Python: los datos y la lógica (el "backend")
├── views/                 ← XML: cómo se ven los datos en pantalla
├── security/              ← quién puede leer/escribir cada modelo
├── data/                  ← datos que se cargan al instalar (los materiales)
├── demo/                  ← datos de ejemplo (la bici y la camiseta)
├── controllers/           ← URLs propias (la página pública /passport/...)
├── report/                ← informes PDF (la etiqueta)
├── static/                ← imágenes, CSS, JS (el icono)
└── tests/                 ← tests automáticos
```

### 3.1 Modelos = tablas de base de datos con lógica
Un **modelo** es una clase Python. Odoo crea automáticamente la tabla en PostgreSQL.
Esto se llama **ORM**: tú no escribes SQL.

```python
class DppMaterial(models.Model):
    _name = "dpp.material"            # nombre del modelo → tabla dpp_material
    name = fields.Char(required=True)  # cada campo es una columna
    emission_factor = fields.Float()
```

Tienes tres modelos:

| Archivo | Modelo | Qué guarda |
|---|---|---|
| `models/dpp_material.py` | `dpp.material` | Catálogo de materiales y su factor de emisión |
| `models/dpp_product_material.py` | `dpp.product.material` | Cada línea de la composición de un producto |
| `models/product_template.py` | `product.template` (heredado) | Añade los campos del pasaporte al producto de Odoo |

### 3.2 Herencia: modificar lo que ya existe
Odoo ya tiene un modelo de producto. En lugar de crear otro, lo **extendemos**:

```python
class ProductTemplate(models.Model):
    _inherit = "product.template"   # "añade cosas al producto existente"
    dpp_enabled = fields.Boolean()
```

Es la idea más importante de Odoo: **nunca se modifica el código original**, se hereda.
Lo mismo pasa con las vistas (`inherit_id` en `views/product_template_views.xml`) y con métodos
como `create()` y `write()`, donde llamamos a `super()` para mantener el comportamiento original.

### 3.3 Relaciones entre modelos
- `Many2one`: "muchos a uno". Cada línea de composición tiene **un** material → `material_id`.
- `One2many`: lo inverso. Un producto tiene **muchas** líneas → `dpp_material_line_ids`.
- `related`: copia un valor de un registro relacionado (`recyclable = related="material_id.recyclable"`).

### 3.4 Campos calculados: el corazón de la huella de carbono
```python
co2_kg = fields.Float(compute="_compute_co2_kg", store=True)

@api.depends("weight_kg", "recycled_pct", "material_id.emission_factor")
def _compute_co2_kg(self):
    for line in self:
        ...
```
- `compute=`: el valor no se escribe a mano, lo calcula un método.
- `@api.depends(...)`: le dice a Odoo **cuándo recalcular**. Si cambias el peso, se recalcula solo.
  Incluso si cambias el factor de un material, se recalculan todos los productos que lo usan.
- `store=True`: se guarda en la base de datos, así se puede buscar, ordenar y agrupar por ese campo.

La fórmula de cada línea es:

```
CO2e = peso × [(1 − %reciclado) × factor_virgen + %reciclado × factor_reciclado]
```

Y el total del producto es: materiales + fabricación + transporte. La nota A–E depende de los kg de CO2e por kg de producto.

### 3.5 Validaciones
`@api.constrains` lanza un error si los datos no tienen sentido (por ejemplo un 120 % de reciclado).
`_sql_constraints` hace lo mismo a nivel de base de datos (códigos únicos, factores no negativos).

### 3.6 `self` y los recordsets
En Odoo, `self` no es un solo registro sino un **conjunto** (recordset). Por eso casi todos los métodos
empiezan con `for record in self:`. `self.ensure_one()` comprueba que solo hay uno.
`self.env["dpp.material"]` te da acceso a cualquier modelo.

### 3.7 Vistas XML
Describen la pantalla, no se programan:
- `<list>`: tabla con varios registros.
- `<form>`: ficha de un registro.
- `<search>`: filtros y agrupaciones del buscador.
- `invisible="not dpp_enabled"`: oculta algo según el valor de un campo.

Una **acción** (`ir.actions.act_window`) dice "abre este modelo con estas vistas" y un **menú** (`menuitem`) la muestra.

### 3.8 Seguridad
`security/ir.model.access.csv` define quién puede hacer qué con cada modelo:
los usuarios internos pueden leer materiales y los administradores crearlos o borrarlos.
**Sin este archivo nadie (salvo el superusuario) podría ver tus modelos.**

### 3.9 Controladores: tu propia URL
`controllers/main.py` crea `/passport/<token>` con `auth="public"`, es decir, sin iniciar sesión.
Usa `sudo()` porque el visitante anónimo no tiene permisos, y por eso solo mostramos los campos
que devuelve `_dpp_public_data()`. El token es aleatorio para que nadie pueda adivinar URLs de otros productos.

### 3.10 QWeb: plantillas HTML
`views/passport_templates.xml` y `report/passport_label_report.xml` usan **QWeb**, el motor de plantillas de Odoo:
- `t-out="..."` escribe un valor.
- `t-if="..."` muestra algo solo si se cumple una condición.
- `t-foreach="..." t-as="line"` repite un bloque para cada elemento.
- `t-call="..."` reutiliza otra plantilla.

### 3.11 Tests
- `TransactionCase` (`tests/test_footprint.py`): prueba la lógica. Cada test se deshace al acabar.
- `HttpCase` (`tests/test_public_page.py`): hace peticiones HTTP reales a la página pública.

---

## 4. Python que te conviene repasar
Lo justo para entender todo el código del módulo:

1. **Clases y herencia** (`class A(B)`, `super()`). Es la base de todo Odoo.
2. **Decoradores** (`@api.depends`, `@api.model`): qué son y cómo se usan.
3. **Listas, diccionarios y comprensiones** (`[x for x in lista if ...]`, `sum(...)`).
4. **`lambda`** y funciones como `filtered()` y `mapped()` de Odoo.
5. **Excepciones** (`raise`, `try/except`).

Recursos oficiales:
- Tutorial oficial "Server framework 101": https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101.html
- Referencia del ORM: https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html
- Código de la OCA (miles de módulos reales para aprender): https://github.com/OCA

---

## 5. Próximas fases (hoja de ruta)

| Fase | Qué añadir | Qué aprendes |
|---|---|---|
| 1 ✅ | Modelos, huella, QR, página pública, etiqueta PDF, tests | ORM, vistas, controladores, QWeb |
| 2 | **Traducción al español** (`i18n/es.po`) | Internacionalización |
| 3 | **Pasaporte por número de serie** (`stock.lot`): cada unidad con su historial | Depender de Inventario |
| 4 | **Huella desde la lista de materiales** (`mrp.bom`) en vez de introducirla a mano | Fabricación, cálculos recursivos |
| 5 | **Alcance 3 desde compras**: emisiones por proveedor o categoría | Contabilidad/Compras, informes |
| 6 | **Panel en OWL** con gráficos de huella por categoría | Frontend moderno de Odoo (JavaScript) |
| 7 | **GitHub Actions** que ejecuten los tests en cada cambio | CI/CD |
| 8 | **Estándar GS1 Digital Link** en el QR y JSON-LD | Interoperabilidad, estándares reales |

---

## 6. Cómo presentarlo en tu CV

**Título:** *Digital Product Passport for Odoo 18 — EU ESPR compliance module*

> Developed an Odoo 18 module that generates EU-style Digital Product Passports: material composition,
> automatic carbon-footprint calculation (kg CO2e), circularity indicators and a public QR-code page with
> a JSON API. Python ORM, XML views, QWeb, HTTP controllers, PDF reports, automated tests and Docker.

Consejos:
- Súbelo a GitHub con el README en inglés y **capturas** de la ficha, la página pública y la etiqueta.
- Graba un **vídeo de 2 minutos**: crear producto → añadir materiales → escanear QR con el móvil.
- En la entrevista explica **por qué** importa (normativa ESPR) y **una decisión técnica** (por ejemplo, el token aleatorio y `sudo()` limitado a campos públicos).
