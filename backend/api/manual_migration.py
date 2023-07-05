# Manual migrations to import a custom dataset.
# Used to populate the database like fixtures do,
#   but with custom real data.
#
# Follow the steps below:

# 0. Create an empty migration file with:
#       docker-compose exec web pipenv run ./manage.py makemigrations --empty api

# 1. From the created file, import this one like below:
#     from backend.api.manual_migration import import_dataset

# 2. Then inside the created file, in the Migration class, paste the following:

#     initial = True
#     operations = [
#         migrations.RunPython(import_dataset, reverse_code=migrations.RunPython.noop)
#     ]

# 3. Then run the migrations with
#       docker-compose exec web pipenv run ./manage.py migrate

from django.db import transaction, IntegrityError
from django.conf import settings
import pandas as pd
import hashlib
import glob
import os


# if negative, all images are registered in database
DJANGO_APP_NAME = "api"
MAX_REGISTERED_IMAGES = -1


def _checksum(file_path):
    """Computes the SHA256 checksum of a file."""
    BUF_SIZE = 2**16    # chunk size
    checksum = hashlib.sha256()
    with open(file_path, 'rb') as fp:
        while True:
            chunk = fp.read(BUF_SIZE)
            if not chunk:
                break
            checksum.update(chunk)

    return checksum.hexdigest()

#image type
def _list_images(ds_path, csv_data, extension=".png"):
    """Lists images in ds_path matching a file extension."""
    dataset_images = []

    #debug
    print("csv data", csv_data)

    for number in csv_data['image_id']:
        img_filename = str(number) + extension
        img_path = os.path.join(ds_path, img_filename)
        if os.path.isfile(img_path):
            dataset_images.append(img_path)
        else:
            print("Image not found: {}".format(img_path))
    
    if MAX_REGISTERED_IMAGES > 0:
        dataset_images = dataset_images[:MAX_REGISTERED_IMAGES]

    return dataset_images


def _load_csv(csv_path):
    """Returns dataframe given a CSV path."""
    df = pd.read_csv(csv_path, header=None, names=['image_id'])
    return df

def _extract_csv_to_db(csv_entry, csv_fields, db_fields, csv_db_map=dict()):
    """Extracts values from csv entry.

    Args:
        csv_entry: dataframe entry.
        csv_fields: fields to extract from csv_entry
        db_fields: new names for extracted values - same length as `csv_fields`
        csv_db_map (dict->dict): has transformations to apply on the values extracted
            its keys must be in `csv_fields`; the set of keys of the children dicts
            contain all possible values for that field. e.g.:
            { 'eye': {
                'left':     'L',
                'right':    'R',
            }, ... }
    Returns:
        dictionary holding the mapped entries which set of keys is `db_fields`
            and the values are the transformation results.
    """

    image_fields = dict()
    for db, csv in zip(db_fields, csv_fields):
        value = csv_entry.iloc[0][csv]
        image_fields.update({ db: value })

    return image_fields

def import_dataset(apps, schema_editor):
    """
    Import images from the dataset into the database, preprocessing as needed.
    """

    # parameters that you might want to change:

    CSV_LOCATION = "../metadata.csv"
    DB_FIELDS   = ['image_id']
    CSV_FIELDS  = ['image_id']
    CSV_DB_MAP = {        # maps old csv values to new database ones
        'image_id': {
            'image_id': 'image_id',
        },
    }

    # load other variables
    Image = apps.get_model(DJANGO_APP_NAME, "Image")
    DATASET_ROOT = settings.DATASET_ROOT

    # load csv file
    df = _load_csv(csv_path=os.path.join(DATASET_ROOT, CSV_LOCATION))
    #debug
    print("df",df)

    # get list of images and metadata
    dataset_images = _list_images(ds_path=DATASET_ROOT, csv_data=df)
    
    #add the images to the database

    # for each image file, extract metadata and create a database entry
    print("\n\tAdding database entries for {} images found...".format(len(dataset_images)))
    counters = {
        '404': 0,
        'new': 0,
        'dup': 0,
    }

    for img_ds_path in dataset_images:

        img_id      = _checksum(img_ds_path)
        extension   = img_ds_path.split('/')[-1].split('.')
        extension   = extension[-1] if len(extension) > 1 else ""
        img_path    = (img_ds_path.split(DATASET_ROOT)[1]).strip(os.path.sep)

        # skip image if already registered
        if Image.objects.filter(img_id=img_id).exists():
            print("Skipping duplicated element:\n\t{}\tSHA256: {}".format(
                img_path, img_id))
            counters['dup'] += 1
            continue

        # extract number from image filename
        number = int(os.path.basename(img_path).split('.')[0])

        #debug
        print(number)
        print(df['image_id'].values)

        image_ids = df['image_id'].tolist()
    
        #check if the number is in the csv file
        if number not in image_ids:
            print("Skipping image not found in csv:\n\t{}\tSHA256: {}".format(
                img_path, img_id))
            counters['404'] += 1
            continue

        # extract values from csv entry
        csv_entry = df.loc[df['image_id'] == number]
        image_fields = _extract_csv_to_db(
            csv_entry=csv_entry,
            csv_fields=CSV_FIELDS,
            db_fields=DB_FIELDS,
            csv_db_map=CSV_DB_MAP,
        )

        # create database object
        img = Image(
            img_id      = img_id,
            extension   = extension,
            img_path    = img_path,
            **image_fields,
        )

        # execute database transaction
        try:
            with transaction.atomic():
                img.save()
                counters['new'] += 1
        except IntegrityError as err:
            print(" >> Failed to load entry from CSV into DB:")
            print(image_fields)
            raise err

    print("\n >> Duplicated entries:  {}".format(counters['dup']))
    print(" >> Entries not found:   {}".format(counters['404']))
    print(" >> Entries added:       {}".format(counters['new']))
