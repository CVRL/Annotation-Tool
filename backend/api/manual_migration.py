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
import csv


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
def _list_images(ds_path, extension=".JPG"):
    """Lists images in ds_path matching a file extension."""
    dataset_images = glob.glob(os.path.join(ds_path, "*" + extension))
    if MAX_REGISTERED_IMAGES > 0:
        dataset_images = dataset_images[:MAX_REGISTERED_IMAGES]
    return dataset_images


def _load_csv(csv_path):
    """Returns dataframe given a CSV path."""
    df = pd.read_csv(csv_path)
    FILENAME = 'filename'
    df = df.set_index(FILENAME)
    df.sort_values(by=[FILENAME])


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
        value = None
        try:
            value = csv_entry.loc[csv]
        except:
            print(csv_entry.head())
            raise
        if csv in csv_db_map:     # translate value
            value = csv_db_map[csv][value]
        image_fields.update({ db: value })

    return image_fields

def import_dataset(apps, schema_editor):
    """
    Import images from the dataset into the database, preprocessing as needed.
    """

    # parameters that you might want to change:

    CSV_LOCATION = "../metadata.csv"
    DB_FIELDS   = ['user_id', 'sample_id', 'eye', 'lens_type', 'nir_illumination', 'lens_brand', 'is_regular']
    CSV_FIELDS  = ['user_id', 'sample_id', 'eye', 'live_fake', 'NIR_illumination', 'lens_brand', 'regular_irregular_lens_type']
    CSV_DB_MAP = {        # maps old csv values to new database ones
        'live_fake': {
            'live':     'L',
            'fake':     'F',
            'clear':    'C',
        },
        'eye': {
            'left':     'L',
            'right':    'R',
        },
        'NIR_illumination': {
            'cross':    'C',
            'direct':   'D',
        },
        'regular_irregular_lens_type': {
            'regular':      True,
            'irregular':    False,
            'none':         None,
            'clear':        None,
        }
    }

    # load other variables
    Image = apps.get_model(DJANGO_APP_NAME, "Image")
    DATASET_ROOT = settings.DATASET_ROOT

    # get list of images and metadata
    dataset_images = _list_images(ds_path=DATASET_ROOT)

    #check if csv file exists
    if not os.path.exists(os.path.join(DATASET_ROOT, CSV_LOCATION)):
        with open(os.path.join(DATASET_ROOT, CSV_LOCATION), 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(CSV_FIELDS)

    df = _load_csv(csv_path=os.path.join(DATASET_ROOT, CSV_LOCATION))

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

        # extract file name from image path
        filename = os.path.basename(img_path).split('.')[0]
        csv_entry = None
        try:
            csv_entry = df.loc[filename]
            if csv_entry.shape[0] > len(CSV_FIELDS):
                # metadata might have duplicated filenames, if so, skip them
                print("Discarding {} entries: filename must be unique!".format(csv_entry.shape[0]))
                continue
        except:
            counters['404'] += 1
            print("Skipping CSV filename not found: {}".format(filename))
            continue

        # extract values from csv entry
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
