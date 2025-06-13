from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

# Replace with your actual URI and database
client = MongoClient("mongodb+srv://eliwaindah:eliwaindaheliwashitojossie@cluster0.jyz0y.mongodb.net/")
db = client["poa_publishers"]
books = db.books

updated_count = 0

for book in books.find():
    update_fields = {}

    # Normalize price
    if "price" in book:
        try:
            price = float(book["price"])
        except (ValueError, TypeError):
            price = 0.0
    else:
        price = 0.0
    update_fields["price"] = price

    # Add or correct is_free
    update_fields["is_free"] = price == 0.0

    # Ensure status exists
    if "status" not in book:
        update_fields["status"] = "pending"
        
        
    if "featured" not in book: 
            update_fields["featured"] = "False"

    # Ensure tags exists
    if "tags" not in book:
        update_fields["tags"] = []

    # Ensure author_name exists
    if "author_name" not in book:
        update_fields["author_name"] = book.get("author", "Unknown")

    # Normalize uploaded_at if string (optional: convert to datetime)
    if "uploaded_at" in book and isinstance(book["uploaded_at"], str):
        try:
            update_fields["uploaded_at"] = datetime.fromisoformat(book["uploaded_at"].replace("Z", "+00:00"))
        except Exception:
            update_fields["uploaded_at"] = datetime.utcnow()
    elif "uploaded_at" not in book:
        update_fields["uploaded_at"] = datetime.utcnow()

    # Update document if needed
    if update_fields:
        books.update_one({"_id": book["_id"]}, {"$set": update_fields})
        updated_count += 1

print(f"✅ Normalized {updated_count} book documents.")
