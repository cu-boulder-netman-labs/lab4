from flask import Flask, render_template

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/get_config")
    def get_config():
        return render_template("get_config.html")


    @app.route("/ospf_config")
    def ospf_config():
        return render_template("ospf_config.html")


    @app.route("/diff_config")
    def diff_config():
        return render_template("diff_config.html")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)