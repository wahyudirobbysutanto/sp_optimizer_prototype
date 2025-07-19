from flask import Flask, render_template, request, redirect, url_for, jsonify

from app.db_connector import connection
from app.optimization.sp_loader import get_stored_procedures, get_sp_definition, get_tables, get_table_columns, get_slow_sp
from app.optimization.sp_optimizer import optimize_stored_procedure, sanitize_sql
from app.optimization.sp_saver import rename_sp_name, save_optimized_sp, save_sql_to_file
from app.indexing.fragmentation_analyzer import analyze_index_fragmentation, generate_maintenance_sql
from app.indexing.index_ai import get_index_recommendation
from app.indexing.sql_executor import execute_sql_statements
from app.indexing.recommendation_builder import generate_recommendation_procedure
from app.utils.utils import is_similar_sql, log_result, log_to_sql, extract_table_names_from_sql, get_existing_index_info
from app.utils.logger import log_action

from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    db_name = os.getenv("SQL_DATABASE")
    sps = get_stored_procedures(connection, db_name)
    sps = [sp for sp in sps if not sp['is_encrypted']]
    return render_template("index.html", stored_procs=sps, db_name=db_name)

@app.route("/analyze", methods=["POST"])
def analyze_index():
    db_name = os.getenv("SQL_DATABASE")
    results = analyze_index_fragmentation(connection, db_name)
    results = [r for r in results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
    
    maintenance_sql = generate_maintenance_sql(results)
    execute_sql_statements(connection, maintenance_sql)
    
    filename = f"index_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    save_sql_to_file(maintenance_sql, filename)

    # ← Ambil daftar SP (misalnya pakai fungsi get_stored_procedures)
    all_sps = get_stored_procedures(connection, db_name)
    sps_for_ui = [
        {"schema": sp["schema"], "name": sp["name"]}
        for sp in all_sps if not sp["is_encrypted"]
    ]

    return render_template(
        "index_result.html",
        index_result=results,
        maintenance_sql=maintenance_sql,
        sp_list=sps_for_ui,
        ai_ready=False
    )

@app.route("/analyze_ai", methods=["POST"])
def analyze_ai():
    try:
        db_name = os.getenv("SQL_DATABASE")
        data = request.get_json()
        selected_sp = data.get("selected_sp")  # Contoh: "Production.uspGetBillOfMaterials"

        if not selected_sp or "." not in selected_sp:
            return jsonify({"ai_suggestions": "-- SP is invalid or not selected."})

        schema, name = selected_sp.split(".", 1)

        # Ambil isi SP
        try:
            sp_text = get_sp_definition(connection, db_name, schema, name)
        except Exception as e:
            print(f"[ERROR] Failed to retrieve SP contents {selected_sp}: {e}")
            return jsonify({"ai_suggestions": f"-- Failed to read SP: {selected_sp}"})

        # Cari tabel yang digunakan dalam SP
        table_names = extract_table_names_from_sql(sp_text)
        # print(sp_text)
        print(f"[DEBUG] Tables found in SP: {table_names}")
        # print(table_names)
        # exit()

        # Ambil struktur kolom tabel yang ditemukan
        table_info_lines = []
        for table in table_names:
            try:
                sch, tbl = table.split(".", 1)
                cols = get_table_columns(connection, db_name, sch, tbl)
                table_info_lines.append(f"{sch}.{tbl} ({', '.join(cols)})")
            except Exception as e:
                print(f"[ERROR] Failed to fetch column for {table}: {e}")

        table_section = "\n".join(table_info_lines)

        # Ambil index yang sudah ada untuk tabel-tabel tersebut
        existing_index_info = get_existing_index_info(connection, table_names)

        # Kirim ke AI
        ai_suggestions = get_index_recommendation(sp_text, table_section, existing_index_info)

        if not ai_suggestions:
            ai_suggestions = "-- (No AI recommendations)"
        else:
            save_sql_to_file(ai_suggestions, "index_ai_recommendations.sql")

        return jsonify({"ai_suggestions": ai_suggestions})

    except Exception as e:
        print("❌ ERROR WHILE RUNNING /analyze_ai:")
        import traceback
        traceback.print_exc()
        return jsonify({"ai_suggestions": f"❌ Internal error: {str(e)}"}), 500


@app.route("/build_index_proc", methods=["POST"])
def build_index_proc():
    db_name = os.getenv("SQL_DATABASE")


    # Analisis fragmentasi terbaru
    frag_results = analyze_index_fragmentation(connection, db_name)
    frag_results = [r for r in frag_results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
    frag_sql = generate_maintenance_sql(frag_results)


    # Baca AI suggestions jika tersedia
    ai_sql = ""
    try:
        with open("outputs/index_ai_recommendations.sql", "r", encoding="utf-8") as f:
            ai_sql = f.read().strip()
    except FileNotFoundError:
        print("❗ AI recommendation file not found. Skip AI index.")

    # Gabungkan SQL
    final_sql = frag_sql.strip()

    if ai_sql and request.form.get("ai_used") == "1":
        final_sql += "\n\n-- AI Suggestions --\n" + ai_sql
    
    
    # Siapkan SQL untuk membuat SP recommendation_index
    sp_sql = f"""
    USE [{db_name}];

    IF OBJECT_ID('dbo.recommendation_index', 'P') IS NOT NULL
        DROP PROCEDURE dbo.recommendation_index;

    EXEC('
    CREATE PROCEDURE dbo.recommendation_index
    AS
    BEGIN
        SET NOCOUNT ON;

        {final_sql.replace("'", "''")}
    END
    ');
    """
    # print("xxxxx")
    # print(frag_results)

    if final_sql == "":
        db_name = os.getenv("SQL_DATABASE")
        results = analyze_index_fragmentation(connection, db_name)
        results = [r for r in results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
        
        maintenance_sql = generate_maintenance_sql(results)
        execute_sql_statements(connection, maintenance_sql)
        
        filename = f"index_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        save_sql_to_file(maintenance_sql, filename)

        # ← Ambil daftar SP (misalnya pakai fungsi get_stored_procedures)
        all_sps = get_stored_procedures(connection, db_name)
        sps_for_ui = [
            {"schema": sp["schema"], "name": sp["name"]}
            for sp in all_sps if not sp["is_encrypted"]
        ]
        return render_template(
            "index_result.html",
            index_result=results,
            maintenance_sql=maintenance_sql,
            sp_list=sps_for_ui,
            ai_ready=False
        )


    try:
        save_optimized_sp(connection, sp_sql)
        # return "✅ Stored Procedure <code>recommendation_index</code> berhasil dibuat!"

        save_sql_to_file(sp_sql, "recommendation_index.sql")

        log_action(
            action="Index Optimization + AI Index Recommendation",
            sp_name="dbo.recommendation_index",
            status="success",
            details=f"Optimized version saved as dbo.recommendation_index"
        )

        return render_template("save_result_optimize.html", sp_sql=sp_sql)

    except Exception as e:
        print(f"❌ Failed to create SP: {e}")

        log_action(
            action="Index Optimization + AI Index Recommendation",
            sp_name="dbo.recommendation_index",
            status="error",
            details=str(e)
        )

        return f"❌ Failed to create SP: {str(e)}", 500

@app.route("/execute_recommendation_index", methods=["POST"])
def execute_recommendation_index():
    try:
        db_name = os.getenv("SQL_DATABASE")
        cursor = connection.cursor()
        cursor.execute(f"USE [{db_name}]; EXEC dbo.recommendation_index;")
        connection.commit()

        result_message = "✅ Stored Procedure executed successfully."
        return render_template("execution_result.html", result=result_message)

    except Exception as e:
        error_message = f"❌ Failed to run SP: {str(e)}"
        print("❌ Failed to run SP:", e)
        return render_template("execution_result.html", result=error_message), 500



# @app.route("/analyze", methods=["POST"])
# def analyze_index():
    
#     db_name = os.getenv("SQL_DATABASE")
#     results = analyze_index_fragmentation(connection, db_name)
    
#     # Hanya tampilkan index yang butuh tindakan (REBUILD atau REORGANIZE)
#     results = [r for r in results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
    
#     # AI suggestion (opsional)
#     # Ambil satu SP dan info tabel (untuk bahan AI)
#     sps = get_stored_procedures(connection, db_name)
#     sps = [sp for sp in sps if not sp['is_encrypted']]
#     if not sps:
#         return "❌ Tidak ada SP yang bisa dianalisis."

#     # sp = sps[0]  # Atau kamu bisa ganti sesuai logika pilihan
#     # sp_text = get_sp_definition(connection, db_name, sp['schema'], sp['name'])

#     combined_sp_text = ""
#     for sp in sps:
#         sp_text = get_sp_definition(connection, db_name, sp['schema'], sp['name'])
#         combined_sp_text += f"-- {sp['schema']}.{sp['name']} --\n{sp_text}\n\n"

#     tables = get_tables(connection, db_name)
#     table_info_lines = []
#     for tbl in tables:
#         cols = get_table_columns(connection, db_name, tbl['schema'], tbl['table'])
#         line = f"{tbl['schema']}.{tbl['table']} ({', '.join(cols)})"
#         table_info_lines.append(line)
#     table_info_text = "\n".join(table_info_lines)

#     cursor = connection.cursor()
#     cursor.execute("""
#         SELECT 
#             s.name AS schema_name,
#             t.name AS table_name,
#             i.name AS index_name,
#             c.name AS column_name
#         FROM sys.indexes i
#         JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
#         JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
#         JOIN sys.tables t ON i.object_id = t.object_id
#         JOIN sys.schemas s ON t.schema_id = s.schema_id
#         WHERE i.is_primary_key = 0 AND i.is_unique_constraint = 0
#     """)
    
#     index_lines = []
#     for row in cursor.fetchall():
#         line = f"{row.schema_name}.{row.table_name}.{row.column_name} --> Indexed as [{row.index_name}]"
#         index_lines.append(line)

#     existing_index_info = "\n".join(index_lines)

#     full_table_info = f"{table_info_text}\n\n=== EXISTING INDEXES ===\n{existing_index_info}"


#     ai_suggestions = get_index_recommendation(combined_sp_text, full_table_info)

#     if ai_suggestions is None:
#         ai_suggestions = "-- (Tidak ada rekomendasi AI)"
    

#     # Buat SQL untuk REBUILD/REORGANIZE
#     maintenance_sql = generate_maintenance_sql(results)

#     # Gabungkan semua rekomendasi
#     final_sql = maintenance_sql
#     if ai_suggestions:
#         final_sql += "\n-- AI Suggestions --\n" + ai_suggestions
#         save_sql_to_file(ai_suggestions, "index_ai_recommendations.sql")        

#     execute_sql_statements(connection, maintenance_sql)
    
#     # Simpan ke file
#     filename = f"index_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
#     save_sql_to_file(final_sql, filename)  # biarkan fungsi yang mengatur folder


#     return render_template("index_result.html", index_result=results, maintenance_sql=final_sql)

# @app.route("/build_index_proc", methods=["POST"])
# def build_index_proc():
#     db_name = os.getenv("SQL_DATABASE")

#     # Ambil hasil fragmentasi ulang (agar tetap up-to-date)
#     frag_results = analyze_index_fragmentation(connection, db_name)
#     frag_results = [r for r in frag_results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
#     frag_sql = generate_maintenance_sql(frag_results)

#     # Ambil hasil AI dari file
#     ai_sql = ""
#     try:
#         with open("outputs/index_ai_recommendations.sql", "r", encoding="utf-8") as f:
#             ai_sql = f.read()
#     except FileNotFoundError:
#         print("❗️ File AI recommendation tidak ditemukan. Lewati AI index.")

#     # Gabungkan semua SQL
#     final_sql = frag_sql
#     if ai_sql:
#         final_sql += "\n-- AI Suggestions --\n" + ai_sql

#     # Bungkus sebagai SP
#     sp_sql = f"""
#     USE [{db_name}];

#     IF OBJECT_ID('dbo.recommendation_index', 'P') IS NOT NULL
#         DROP PROCEDURE dbo.recommendation_index;

#     EXEC('
#     CREATE PROCEDURE dbo.recommendation_index
#     AS
#     BEGIN
#         SET NOCOUNT ON;

#         {final_sql.replace("'", "''")}
#     END
#     ');
#     """
    
#     save_optimized_sp(connection, sp_sql)

#     return "✅ Stored Procedure <code>recommendation_index</code> berhasil dibuat!"


@app.route("/optimize", methods=["GET"])
def optimize_page():
    db_name = os.getenv("SQL_DATABASE")
    sps = get_stored_procedures(connection, db_name)
    sps = [sp for sp in sps if not sp["is_encrypted"]]
    return render_template("optimize.html", stored_procedures=sps, db_name=db_name)

@app.route("/optimize_sp", methods=["POST"])
def optimize():
    db_name = os.getenv("SQL_DATABASE")
    sp_full = request.form.get("sp_name")

    if not sp_full or "." not in sp_full:
        return "❌ Invalid SP data. Please select SP from the list."

    schema, name = sp_full.split(".")

    sp_text = get_sp_definition(connection, db_name, schema, name)
    if not sp_text:
        return f"Failed to retrieve SP definition {schema}.{name}"

    tables = get_tables(connection, db_name)
    table_info_lines = []
    for tbl in tables:
        cols = get_table_columns(connection, db_name, tbl['schema'], tbl['table'])
        line = f"{tbl['schema']}.{tbl['table']} ({', '.join(cols)})"
        table_info_lines.append(line)
    table_info = "\n".join(table_info_lines)

    optimized_sql = optimize_stored_procedure(sp_text, table_info)
    if not optimized_sql:
        return "❌ Optimization failed (AI did not respond)."

    optimized_sql = sanitize_sql(optimized_sql)
    optimized_sql = optimized_sql.replace("=== END SP_OPTIMIZED ===", "")
    optimized_sql = optimized_sql.replace("=== SP_OPTIMIZED ===", "")

    similar, ratio = is_similar_sql(sp_text, optimized_sql)

    return render_template("result.html", original=sp_text, optimized=optimized_sql,
                           schema=schema, name=name, similarity=round(ratio * 100, 2),
                           similar=similar)

@app.route("/save", methods=["POST"])
def save():
    db_name = os.getenv("SQL_DATABASE")
    sql_text = request.form.get("sql")
    schema = request.form.get("schema")
    name = request.form.get("name")

    optimized_sql, new_name = rename_sp_name(sql_text)
    success = save_optimized_sp(connection, optimized_sql)
    status = "success" if success else "fail"

    # log_to_sql(connection, name, status)
    
    log_action(
        action="Index Optimization + AI Index Recommendation",
        sp_name=new_name,
        status=status,
        details=f"Optimized version saved as {new_name}"
    )

    return render_template(
        "save_result.html",
        status=status,
        original_name=f"{schema}.{name}",
        new_sp_name=f"{schema}.{new_name}",
        db_name=db_name
    )


# @app.route("/optimize", methods=["POST"])
# def optimize():
#     db_name = os.getenv("SQL_DATABASE")
#     sp_full = request.form.get("name")

#     if not sp_full or "|" not in sp_full:
#         return "❌ Data SP tidak valid. Harap pilih SP dari daftar."

#     schema, name = sp_full.split("|")

#     sp_text = get_sp_definition(connection, db_name, schema, name)
#     if not sp_text:
#         return f"Gagal ambil definisi SP {schema}.{name}"

#     tables = get_tables(connection, db_name)
#     table_info_lines = []
#     for tbl in tables:
#         cols = get_table_columns(connection, db_name, tbl['schema'], tbl['table'])
#         line = f"{tbl['schema']}.{tbl['table']} ({', '.join(cols)})"
#         table_info_lines.append(line)
#     table_info = "\n".join(table_info_lines)

#     optimized_sql = optimize_stored_procedure(sp_text, table_info)
#     if not optimized_sql:
#         return "❌ Optimasi gagal (AI tidak memberi respon)."

#     optimized_sql = sanitize_sql(optimized_sql)
#     similar, ratio = is_similar_sql(sp_text, optimized_sql)

#     return render_template("result.html", original=sp_text, optimized=optimized_sql,
#                            schema=schema, name=name, similarity=round(ratio*100, 2),
#                            similar=similar)

# @app.route("/save", methods=["POST"])
# def save():
#     db_name = os.getenv("SQL_DATABASE")
#     sql_text = request.form.get("sql")
#     name = request.form.get("name")

#     optimized_sql, new_name = rename_sp_name(sql_text)
#     status = "success" if save_optimized_sp(connection, optimized_sql) else "fail"
#     log_to_sql(connection, name, status)
#     return redirect("/")

@app.route("/slow-sp")
def slow_sp():
    data = get_slow_sp(connection)
    return render_template("slow_sp.html", rows=data)


if __name__ == "__main__":
    app.run(debug=True)
