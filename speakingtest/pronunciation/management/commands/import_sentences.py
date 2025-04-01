import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from pronunciation.models import Sentence
from django.db import transaction

class Command(BaseCommand):
    help = 'Import sentences from CSV file into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='data_en.csv',
            help='CSV file path (relative to sentences directory)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sentences before import'
        )

    def handle(self, *args, **options):
        # Get the full path to the CSV file
        file_name = options['file']
        csv_path = os.path.join(settings.BASE_DIR, 'pronunciation', 'sentences', file_name)

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_path}'))
            return

        # Clear existing sentences if requested
        if options['clear']:
            self.stdout.write('Clearing existing sentences...')
            Sentence.objects.all().delete()

        # Count sentences before import
        count_before = Sentence.objects.count()

        # Begin transaction for better performance
        with transaction.atomic():
            imported_count = 0
            skipped_count = 0

            with open(csv_path, 'r', encoding='utf-8') as csv_file:
                reader = csv.DictReader(csv_file)
                
                for row in reader:
                    sentence_text = row.get('sentence', '').strip()
                    
                    # Skip empty sentences or those exceeding max length
                    if not sentence_text or len(sentence_text) > 500:
                        skipped_count += 1
                        continue
                    
                    # Determine difficulty based on sentence length
                    length = len(sentence_text.split())
                    if length <= 5:
                        difficulty = 'easy'
                    elif length <= 12:
                        difficulty = 'medium'
                    else:
                        difficulty = 'hard'
                    
                    # Create sentence
                    Sentence.objects.create(
                        text=sentence_text,
                        difficulty=difficulty
                    )
                    imported_count += 1
                    
                    # Show progress every 100 sentences
                    if imported_count % 100 == 0:
                        self.stdout.write(f'Imported {imported_count} sentences...')

        # Show final statistics
        self.stdout.write(self.style.SUCCESS(
            f'Import complete! Added {imported_count} sentences, skipped {skipped_count} sentences. '
            f'Total sentences in database: {count_before + imported_count}'
        ))
