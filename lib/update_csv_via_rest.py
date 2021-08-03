# update csv via POST
from flask import request

from io import StringIO
import csv


def build_route(app, csv_name):
    @app.server.route("/update_csv", methods=["POST"])
    def parse_request():
        postdata = request.get_data()

        f = StringIO(postdata.decode("utf-8"))
        reader = csv.reader(f, delimiter=",")

        # write result back to file
        writer = csv.writer(open(csv_name, "w"))
        for row in reader:
            writer.writerow(row)

        return "ok"
