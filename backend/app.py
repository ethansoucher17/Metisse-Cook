import os
import mysql.connector
from flask import Flask, render_template
from dotenv import load_dotenv
from flask import request, redirect, url_for, flash, get_flashed_messages
from flask_mail import Mail, Message

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Connexion MySQL avec mysql-connector
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=os.getenv("DB_PORT")
    )

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "metissecook@gmail.com"
app.config['MAIL_PASSWORD'] = "wfan ywth exng bmdm"
app.config['MAIL_DEFAULT_SENDER'] = "metissecook@gmail.com"

mail = Mail(app)

@app.route("/")
def accueil():
    return render_template("index.html")

@app.route("/prestations")
def prestations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT titre, type, description, image_url FROM prestations")
    prestations = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("prestations.html", prestations=prestations)

@app.route("/admin/prestations")
def admin_prestations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, titre, type, description FROM prestations")
    prestations = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_prestations.html", prestations=prestations)

@app.route("/admin/prestations/ajouter", methods=["GET", "POST"])
def ajouter_prestation():
    if request.method == "POST":
        titre = request.form['titre']
        type_ = request.form['type']
        description = request.form['description']
        image_url = request.form['image_url']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO prestations (titre, type, description, image_url) VALUES (%s, %s, %s, %s)",
            (titre, type_, description, image_url)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Prestation ajoutée avec succès !")
        return redirect(url_for('admin_prestations'))

    return render_template("ajouter_prestation.html")

@app.route("/admin/prestations/supprimer/<int:id>", methods=["POST"])
def supprimer_prestation(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM prestations WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Prestation supprimée avec succès !")
    return redirect(url_for("admin_prestations"))

@app.route("/admin/prestations/modifier/<int:id>", methods=["GET", "POST"])
def modifier_prestation(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        titre = request.form['titre']
        type_ = request.form['type']
        description = request.form['description']
        image_url = request.form['image_url']

        cursor.execute("""
            UPDATE prestations
            SET titre = %s, type = %s, description = %s, image_url = %s
            WHERE id = %s
        """, (titre, type_, description, image_url, id))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Prestation modifiée avec succès !")
        return redirect(url_for("admin_prestations"))

    # GET — afficher le formulaire avec les données actuelles
    cursor.execute("SELECT * FROM prestations WHERE id = %s", (id,))
    prestation = cursor.fetchone()
    cursor.close()
    conn.close()

    if not prestation:
        flash("Prestation introuvable.")
        return redirect(url_for("admin_prestations"))

    return render_template("modifier_prestation.html", prestation=prestation)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        nom = request.form["nom"]
        email = request.form["email"]
        categorie = request.form.get("categorie")
        type_evenement = request.form.get("type_evenement")
        type_prestation = request.form.get("type_prestation")
        message_contenu = request.form["message"]

        msg = Message("Nouvelle demande de contact", recipients=["metissecook@gmail.com"])
        msg.html = f"""
<html>
<body style="font-family: 'Arial', sans-serif; background-color: #f9f7f1; color: #000;">
    <div style="max-width: 600px; margin: auto; padding: 20px;">
        <div style="text-align: center;">
            <img src="https://res.cloudinary.com/dcziks4z1/image/upload/v1749461936/logo_rond_givo7t.png" alt="Logo Métisse Cook" style="max-width: 120px; margin-bottom: 20px;">
            <h2 style="color: #8e8c37;">Nouvelle demande de contact</h2>
        </div>
        <hr style="border: none; border-top: 1px solid #ccc; margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px;"><strong>Nom :</strong></td><td>{nom}</td></tr>
            <tr><td style="padding: 8px;"><strong>Email :</strong></td><td>{email}</td></tr>
            <tr><td style="padding: 8px;"><strong>Catégorie :</strong></td><td>{categorie}</td></tr>
            <tr><td style="padding: 8px;"><strong>Type d’événement :</strong></td><td>{type_evenement}</td></tr>
            <tr><td style="padding: 8px;"><strong>Type de prestation :</strong></td><td>{type_prestation}</td></tr>
        </table>
        <div style="margin-top: 30px;">
            <p style="font-size: 15px;"><strong>Message :</strong></p>
            <div style="background-color: #fff; border-left: 4px solid #8e8c37; padding: 10px 15px; font-style: italic;">
                {message_contenu}
            </div>
        </div>
        <hr style="border: none; border-top: 1px solid #ccc; margin: 30px 0;">
        <p style="text-align: center; font-size: 13px; color: #888;">
            Ce message a été envoyé via le formulaire de contact de Métisse Cook.
        </p>
    </div>
</body>
</html>
"""

        mail.send(msg)
        flash("Votre message a bien été envoyé. Merci !")
        return redirect(url_for("confirmation"))

    return render_template("contact.html")

# Nouvelle route de confirmation
@app.route("/confirmation")
def confirmation():
    return render_template("confirmation.html")

if __name__ == "__main__":
    app.run(debug=True)