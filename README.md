# tech-test-python

## ETL  

```bash
python manage.py load_data
```

## API

GET /api/portfolios/<portfolio_id>/snapshot/?date=YYYY-MM-DD

**Response**

```json
{
"date": "2022-02-15", 
"total_value": "1000000000.00",
 "weights": {
    "ABS": "0.015000",
    "Asia Desarrollada": "0.016000",
    
}
```

## Ejecutar el proyecto

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_data
python manage.py runserver
```
