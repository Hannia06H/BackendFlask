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

# GET productos
@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM productos")
    productos = cur.fetchall()
    cur.close()
    return jsonify(productos)

# POST producto
@app.route('/api/productos', methods=['POST'])
def agregar_producto():
    data = request.json
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO productos (nombre, descripcion, precio, categoria, stock) VALUES (%s, %s, %s, %s, %s)",
                (data['nombre'], data['descripcion'], data['precio'], data['categoria'], data['stock']))
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
            SET nombre=%s, descripcion=%s, precio=%s, categoria=%s, stock=%s
            WHERE id=%s
        """, (
            data['nombre'],
            data['descripcion'],
            data['precio'],
            data['categoria'],
            data['stock'],
            id
        ))
        mysql.connection.commit()
        cur.close()
        return jsonify({"mensaje": "Producto actualizado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(port=5000)
