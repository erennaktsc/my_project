from app import create_app
from app.processor import process_document

app = create_app()

with app.app_context():
    document = process_document('test2.png', num_questions=3)
    print(f"\nBaşarıyla işlendi! Document ID: {document.id}")