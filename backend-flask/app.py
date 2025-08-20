from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mysqldb import MySQL
import config

app = Flask(__name__)
CORS(app)

# Configuración
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)

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
    cur.execute("INSERT INTO productos (nombre, descripcion, precio_compra, precio_venta, categoria_id, stock) VALUES (%s, %s, %s, %s, %s, %s)",
            (data['nombre'], data['descripcion'], data['precio_compra'], data['precio_venta'], data['categoria_id'], data['stock']))

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
        column_names = [desc[0] for desc in cur.description]  # Mover antes del close
        cur.close()
        
        # Convertir a array de diccionarios
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
    
    # Convertir a array de diccionarios
    column_names = [desc[0] for desc in cur.description]
    categorias_list = [dict(zip(column_names, row)) for row in categorias]
    
    cur.close()
    return jsonify(categorias_list)


if __name__ == '__main__':
    app.run(port=5000)
