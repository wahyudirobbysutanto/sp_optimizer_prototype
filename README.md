# 🧠 SQL Server Performance Optimizer (Prototype)

A Flask-based prototype application designed to assist in optimizing SQL Server performance. This system helps detect index fragmentation, provides automated repair suggestions (REBUILD/REORGANIZE), and recommends new indexes using AI based on stored procedure content.

## 🎯 Why This Project Matters

This project showcases how AI can augment traditional DBA workflows — combining query stat analysis, SP parsing, and AI-powered recommendations for practical SQL Server performance improvements.

---

## 🧰 Tech Stack

- Python 3.x
- Flask
- SQL Server (tested with 2019)
- Gemini (via API)
- Jinja2 Templates
- HTML / Bootstrap

---

## 🚀 Key Features

- 🔍 Automatically detect fragmented indexes
- 🧠 AI-based index recommendations (based on SP contents & table structure)
- 📜 Recommendations are consolidated into a single Stored Procedure: `recommendation_index`
- 🛠️ Manual execution via SQL Server or Flask UI
- 🗂 Logs recommendations to `.sql` file for documentation
- ⚙️ SP optimization with AI and visual side-by-side comparison
- 📈 Display slow stored procedures via SQL Server DMV
- 🧾 Action logging to `.json` and SQL table

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/wahyudirobbysutanto/sp_optimizer_prototype.git
cd sp_optimizer_prototype
```

### 2. Create a virtual environment

```bash
python -m venv venv
```
#### Windows:
```bash
venv\Scripts\activate
```
#### Linux/macOS:
```bash
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Database Configuration
Create a `.env` file in the root folder:
```bash
SQL_SERVER=localhost
SQL_DATABASE=AdventureWorks2019
SQL_USERNAME=your_username
SQL_PASSWORD=your_password
```

Replace with your SQL Server credentials.

---

## ▶️ Running the Application
```bash
python run_web.py
```

Open in your browser:
```bash
http://127.0.0.1:5000
```

---

## 🧪 Usage Flow

1. Click "Check Index Fragmentation" to detect fragmented indexes
2. (Optional) Click "Get AI Recommendations" to see additional suggested indexes
3. Click "Save as Stored Procedure" to create `dbo.recommendation_index`
4. Run manually:
```sql
EXEC dbo.recommendation_index;
```

---

## 📄 Example Output

A sample result from AI + fragmentation recommendations saved into a stored procedure:

```sql
CREATE NONCLUSTERED INDEX IX_Production_Product_ProductID
ON Production.Product (ProductID);
CREATE NONCLUSTERED INDEX IX_Production_BillOfMaterials_ComponentID
ON Production.BillOfMaterials (ComponentID);

ALTER INDEX PK_Product_ProductID ON Production.Product REBUILD;
```

---

## 🖼️ Demo Screenshots

### Index Fragmentation Results
![Fragmentation UI](images/fragmentation_ui.png)

### AI-based Index Recommendations
![AI Recommendation](images/ai_index_recommendation.png)

### Optimized Stored Procedure View
![SP Optimization](images/sp_optimization_ui.png)

### Optimized Stored Procedure View
![Index Recommendation Result](images/index_recommendation_result.png)



## 🗃️ Folder Structure
```bash
├── app/
│   ├── indexing/
│   	├── __init__.py
│   	├── fragmentation_analyzer.py
│   	├── index_ai.py
│   	├── index_recommender.py
│   	├── recommendation_builder.py
│   	└── sql_executor.py
│   ├── optimization/
│   	├── __init__.py
│   	├── sp_loader.py
│   	├── sp_optimizer.py
│   	└── sp_saver.py
│   └── utils/
│   	├── __init__.py
│   	├── logger.py
│   	└── utilssaver.py
├── samples/                            # 📁 Sample SP and outputs
│   ├── CustomerSearchLog.sql        
│   ├── generate_fragmentation.sql       
│   ├── uspFindCustomersByRegion.sql        
│   ├── uspGetOrdersByCustomer.sql        
│   └── uspGetProductSalesInfo.sql       
├── logs/                               # 📁 Sample SP and outputs
│   └── log_activity.json
├── outputs/                            # 📁 AI SQL recommendation files
├── templates/ 
│   ├── execution_result.html
│   ├── index.html
│   ├── index_result.html
│   ├── optimize.html
│   ├── result.html
│   ├── save_result.html
│   ├── slow_sp.html
│   └── save_result_optimize.html
├── run_web.py                   
├── requirements.txt
├── .env                         
└── README.md
```
---

## ⚠️ Notes

- Ensure Full Text Search is enabled if your SPs use `FREETEXTTABLE` / `CONTAINSTABLE`
- AI recommendations do **not** modify SP logic, only suggest indexes
- Stored procedure execution is manual and not triggered automatically
- Optimized SPs are saved with `_optimized` suffix for clarity

---

## 📬 Contact & Feedback

If you have questions, suggestions, or want to collaborate, feel free to reach out:

- 💼 LinkedIn: [Wahyudi Robby Sutanto](https://www.linkedin.com/in/wahyudirs/)
- 📧 Email: wahyudirobbysutanto@gmail.com
- 🐙 GitHub: [@wahyudirobbysutanto](https://github.com/wahyudirobbysutanto)

Feedback and contributions are welcome!


---

## 📜 License
MIT License – Free to use for learning, experimentation, and internal development.
