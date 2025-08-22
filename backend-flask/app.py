from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from collections import defaultdict
import config

app = Flask(__name__)
CORS(app)

# -----------------------------
# Configuración MySQL
# -----------------------------
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)

# -----------------------------
# Utilidades
# -----------------------------
def _normalizar_items(items):
    """
    items: [{"id": 1, "cantidad": 2}, {"id": 1, "cantidad": 1}, ...]
    Suma cantidades por id y valida > 0.
    """
    acc = defaultdict(int)
    for it in items:
        pid = int(it.get("id", 0))
        qty = int(it.get("cantidad", 0))
        if pid <= 0 or qty <= 0:
            raise ValueError("Items inválidos (id/cantidad).")
        acc[pid] += qty
    return [{"id": k, "cantidad": v} for k, v in acc.items()]

# -----------------------------
# Rutas de Productos (CRUD)
# -----------------------------

# GET productos con JOIN para obtener nombre de categoría
@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                p.id,
                p.nombre,
                p.descripcion,
                p.precio_compra,
                p.precio_venta,
                p.categoria_id,
                c.nombre as categoria_nombre,
                p.stock
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            ORDER BY p.id DESC
        """)
        productos = cur.fetchall()
        cur.close()
        return jsonify(productos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# POST producto
@app.route('/api/productos', methods=['POST'])
def agregar_producto():
    data = request.json
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO productos (nombre, descripcion, precio_compra, precio_venta, categoria_id, stock) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['nombre'], data['descripcion'], data['precio_compra'], 
        data['precio_venta'], data['categoria_id'], data['stock']
    ))

    mysql.connection.commit()
    cur.close()
    return jsonify({"mensaje": "Producto agregado"})

# DELETE producto
@app.route('/api/productos/<int:id>', methods=['DELETE'])
def eliminar_producto(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM productos WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"mensaje": "Producto eliminado"})

# PUT producto
@app.route('/api/productos/<int:id>', methods=['PUT'])
def actualizar_producto(id):
    data = request.json
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
        UPDATE productos
        SET nombre=%s, descripcion=%s, precio_compra=%s, precio_venta=%s, categoria_id=%s, stock=%s
        WHERE id=%s
    """, (
        data['nombre'],
        data['descripcion'],
        data['precio_compra'],
        data['precio_venta'],
        data['categoria_id'],
        data['stock'],
        id
    ))

        mysql.connection.commit()
        cur.close()
        return jsonify({"mensaje": "Producto actualizado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Reportes y Categorías
# -----------------------------

# GET reporte de productos
@app.route('/api/reportes/productos', methods=['GET'])
def reporte_productos():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                p.id,
                p.nombre,
                p.descripcion,
                p.precio_compra,
                p.precio_venta,
                c.nombre AS categoria,
                p.stock
            FROM productos p
            INNER JOIN categorias c ON p.categoria_id = c.id
        """)

        productos = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]  # antes de cerrar
        cur.close()

        productos_list = [dict(zip(column_names, row)) for row in productos]
        return jsonify(productos_list)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GET categorías
@app.route('/api/categorias', methods=['GET'])
def obtener_categorias():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categorias")
    categorias = cur.fetchall()

    column_names = [desc[0] for desc in cur.description]
    categorias_list = [dict(zip(column_names, row)) for row in categorias]

    cur.close()
    return jsonify(categorias_list)

# -----------------------------
# Endpoints de Stock
# -----------------------------

# POST: descontar stock (transacción con FOR UPDATE)
@app.route('/api/productos/ajustar-stock', methods=['POST'])
def ajustar_stock():
    try:
        data = request.get_json(silent=True) or {}
        items = data.get("items", [])
        if not items:
            return jsonify({"message": "Sin items"}), 400

        items_norm = _normalizar_items(items)

        conn = mysql.connection
        cur = conn.cursor()
        cur.execute("START TRANSACTION")

        # Validar y bloquear filas
        for it in items_norm:
            cur.execute("SELECT stock FROM productos WHERE id = %s FOR UPDATE", (it["id"],))
            row = cur.fetchone()
            if row is None:
                conn.rollback(); cur.close()
                return jsonify({"message": f"Producto {it['id']} no existe"}), 404
            stock_actual = int(row[0])
            if stock_actual < it["cantidad"]:
                conn.rollback(); cur.close()
                return jsonify({
                    "message": f"Stock insuficiente para producto {it['id']}",
                    "stock_actual": stock_actual,
                    "requerido": it["cantidad"]
                }), 409

        # Descontar
        for it in items_norm:
            cur.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (it["cantidad"], it["id"]))

        conn.commit()
        cur.close()
        return jsonify({"message": "Stock actualizado"}), 200

    except ValueError as ve:
        return jsonify({"message": str(ve)}), 400
    except Exception as e:
        try:
            mysql.connection.rollback()
        except Exception:
            pass
        return jsonify({"message": "Error al ajustar stock", "error": str(e)}), 500

# POST: restaurar stock (para rollback si falla guardar venta en Mongo)
@app.route('/api/productos/restaurar-stock', methods=['POST'])
def restaurar_stock():
    try:
        data = request.get_json(silent=True) or {}
        items = data.get("items", [])
        if not items:
            return jsonify({"message": "Sin items"}), 400

        items_norm = _normalizar_items(items)

        conn = mysql.connection
        cur = conn.cursor()
        cur.execute("START TRANSACTION")

        for it in items_norm:
            cur.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", (it["cantidad"], it["id"]))

        conn.commit()
        cur.close()
        return jsonify({"message": "Stock restaurado"}), 200

    except ValueError as ve:
        return jsonify({"message": str(ve)}), 400
    except Exception as e:
        try:
            mysql.connection.rollback()
        except Exception:
            pass
        return jsonify({"message": "Error al restaurar stock", "error": str(e)}), 500


# -----------------------------
# Main
# -----------------------------
if __name__ == '__main__':
    app.run(port=5000)
