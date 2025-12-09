import os
import mysql.connector
from flask import Flask, render_template
from dotenv import load_dotenv
from flask import request, redirect, url_for, flash, get_flashed_messages
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

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
        port=int(os.getenv("DB_PORT")),
        charset='utf8mb4',
        collation='utf8mb4_general_ci'
    )

def get_page_contents(page_slug):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT block_key, content, content_type FROM contents WHERE page_slug = %s",
        (page_slug,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # dict : {'hero_title': '...', 'event_image': '...'}
    return {row["block_key"]: row["content"] for row in rows}

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "metissecook@gmail.com"
app.config['MAIL_PASSWORD'] = "wfan ywth exng bmdm"
app.config['MAIL_DEFAULT_SENDER'] = "metissecook@gmail.com"

mail = Mail(app)

# Dossier d'upload et extensions autorisées
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    contents = get_page_contents("home")
    return render_template("index.html", contents=contents)

@app.route("/accueil")
def accueil():
    return redirect(url_for("index"))

@app.route("/prestations")
def prestations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT titre, description, image_url FROM prestations")
    prestations = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("prestations.html", prestations=prestations)

from functools import wraps
from flask import session

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "utilisateur_id" not in session:
            flash("Connexion requise.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/admin/accueil", methods=["GET", "POST"])
@login_required
def admin_accueil():
    # Récupération des contenus actuels
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT block_key, content, content_type FROM contents WHERE page_slug = %s",
        ("home",),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    contents = {row["block_key"]: row["content"] for row in rows}

    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()

        def update_block(block_key, value):
            cursor.execute(
                """
                UPDATE contents
                SET content = %s
                WHERE page_slug = %s AND block_key = %s
                """,
                (value, "home", block_key),
            )

        # Textes
        update_block("hero_title",        request.form.get("hero_title", ""))
        update_block("about_text",        request.form.get("about_text", ""))
        update_block("event_text",        request.form.get("event_text", ""))
        update_block("quote_text",        request.form.get("quote_text", ""))
        update_block("prestations_text",  request.form.get("prestations_text", ""))

        # Images (upload éventuel)
        for field_name, block_key in [
            ("event_image", "event_image"),
            ("banner_image", "banner_image"),
        ]:
            file = request.files.get(field_name)
            if file and file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                new_url = "/static/uploads/" + filename
                update_block(block_key, new_url)

        conn.commit()
        cursor.close()
        conn.close()

        flash("Page d’accueil mise à jour avec succès !")
        return redirect(url_for("admin_accueil"))

    return render_template("admin_accueil.html", contents=contents)

@app.route("/admin/prestations")
@login_required
def admin_prestations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, titre, description, image_url FROM prestations")
    prestations = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin_prestations.html", prestations=prestations)


@app.route("/admin/prestations/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_prestation():
    if request.method == "POST":
        titre = request.form.get("titre", "").strip()
        description = request.form.get("description", "").strip()

        image_url = None

        file = request.files.get("image_file")
        app.logger.info(f"Fichier reçu pour image_file : {file!r}")

        if file:
            app.logger.info(f"Nom de fichier reçu : {file.filename!r}")
        else:
            app.logger.info("Aucun fichier reçu dans image_file.")

        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = app.config["UPLOAD_FOLDER"]
            app.logger.info(f"Sauvegarde du fichier dans : {upload_folder}/{filename}")
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            image_url = "/static/uploads/" + filename
            app.logger.info(f"image_url stockée en base : {image_url}")
        else:
            app.logger.info("Aucun fichier sauvegardé (soit pas de fichier, soit extension non autorisée).")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO prestations (titre, description, image_url) VALUES (%s, %s, %s)",
            (titre, description, image_url),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Prestation ajoutée avec succès !")
        return redirect(url_for("admin_prestations"))

    return render_template("ajouter_prestation.html")


@app.route("/admin/prestations/supprimer/<int:id>", methods=["POST"])
@login_required
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
@login_required
def modifier_prestation(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM prestations WHERE id = %s", (id,))
    prestation = cursor.fetchone()

    if not prestation:
        cursor.close()
        conn.close()
        flash("Prestation introuvable.")
        return redirect(url_for("admin_prestations"))

    if request.method == "POST":
        titre = request.form["titre"]
        description = request.form["description"]

        image_url = prestation["image_url"]  # image actuelle par défaut

        file = request.files.get("image_file")
        if file and file.filename != "" and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            image_url = "/static/uploads/" + filename

        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE prestations
            SET titre = %s, description = %s, image_url = %s
            WHERE id = %s
            """,
            (titre, description, image_url, id),
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Prestation modifiée avec succès !")
        return redirect(url_for("admin_prestations"))

    cursor.close()
    conn.close()
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        mot_de_passe = request.form["mot_de_passe"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
        utilisateur = cursor.fetchone()
        cursor.close()
        conn.close()

        if utilisateur and check_password_hash(utilisateur["mot_de_passe"], mot_de_passe):
            session["utilisateur_id"] = utilisateur["id"]
            session["utilisateur_email"] = utilisateur["email"]
            flash("Connexion réussie !")
            return redirect(url_for("admin_prestations"))
        else:
            flash("Email ou mot de passe incorrect")

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("Vous avez été déconnecté.")
    return redirect(url_for('index'))

@app.route("/debug_uploads")
def debug_uploads():
    folder = app.config["UPLOAD_FOLDER"]
    try:
        files = os.listdir(folder)
    except FileNotFoundError:
        return f"UPLOAD_FOLDER = {folder}<br>Ce dossier n'existe pas."

    listing = "<br>".join(files) or "(dossier vide)"
    return f"UPLOAD_FOLDER = {folder}<br><br>Fichiers présents :<br>{listing}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)