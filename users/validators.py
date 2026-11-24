from django.core.exceptions import ValidationError


def validate_full_name(value):
    parts = value.split()
    if len(parts) < 2:
        raise ValidationError("Укажите полные имя и фамилию, например «Александр Иванов».")
    for part in parts:
        if sum(char.isalpha() for char in part) < 5:
            raise ValidationError("Имя и фамилия должны содержать хотя бы по пять букв.")
        if not all(char.isalpha() or char in "-'’" for char in part):
            raise ValidationError("В имени допустимы буквы, пробелы, дефисы и апострофы.")


def validate_bio(value):
    if sum(char.isalpha() for char in value) < 70:
        raise ValidationError("Расскажите о себе подробнее: в описании должно быть не менее 70 букв.")
