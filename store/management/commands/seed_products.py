"""
Заполняет базу данных товарами и загружает фото в Cloudinary.

Запуск локально (с Neon DATABASE_URL в .env):
    python manage.py seed_products

Запуск с явным путём к папке с фото:
    python manage.py seed_products --images-dir "C:/path/to/project pictures"
"""
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from store.models import Category, Artisan, Product, ProductVariant


ARTISANS = [
    {
        'name': 'Usta Ramiz Əliyev',
        'region': 'Baku',
        'description': (
            'Master craftsman with over 30 years of experience in traditional '
            'Azerbaijani leather work. Ramiz learned his craft from his father '
            'and continues to use centuries-old techniques from Baku.'
        ),
    },
    {
        'name': 'Murad Ağayev',
        'region': 'Sheki',
        'description': (
            'Renowned artisan from Sheki, specialising in hand-stitched leather '
            'goods with intricate regional patterns. Each piece takes 2–4 weeks '
            'to complete by hand.'
        ),
    },
    {
        'name': 'Kamran Quliyev',
        'region': 'Ganja',
        'description': (
            'Third-generation leather craftsman from Ganja, known for combining '
            'traditional Azerbaijani motifs with modern silhouettes. Winner of '
            'the National Crafts Award 2022.'
        ),
    },
]

# category_slug → (parent_slug, display_name)
CATEGORIES = {
    'leather-goods': (None, 'Leather Goods'),
    'belts':         ('leather-goods', 'Belts'),
    'bags':          ('leather-goods', 'Bags'),
    'boots':         ('leather-goods', 'Boots'),
    'shoes':         ('leather-goods', 'Shoes'),
    'jackets':       ('leather-goods', 'Jackets'),
    'hats':          ('leather-goods', 'Hats'),
    'wallets':       ('leather-goods', 'Wallets'),
    'bracelets':     ('leather-goods', 'Bracelets'),
}

# (name_template, slug_template, category_slug, artisan_idx,
#  price, description, sizes, stock, image_filename)
PRODUCTS = [
    # ── BELTS ──────────────────────────────────────────────────────────
    ('Heritage Leather Belt',      'heritage-leather-belt',      'belts', 0, '95.00',
     'Hand-stitched full-grain leather belt with a solid brass buckle. Develops a rich patina over time.',
     ['S','M','L','XL'], 8, 'belt1.jpg'),
    ('Braided Leather Belt',       'braided-leather-belt',       'belts', 1, '85.00',
     'Classic braided design in vegetable-tanned leather. Fits most standard belt loops.',
     ['S','M','L','XL'], 6, 'belt2.jpg'),
    ('Wide Artisan Belt',          'wide-artisan-belt',          'belts', 2, '110.00',
     'Wide-cut belt ideal for formal wear. Hand-burnished edges, antique silver buckle.',
     ['S','M','L','XL'], 5, 'belt3.jpg'),
    ('Slim Profile Belt',          'slim-profile-belt',          'belts', 0, '80.00',
     'Minimalist slim-cut belt in smooth calfskin. Reversible — black on one side, tan on the other.',
     ['S','M','L','XL'], 7, 'belt4.jpg'),
    ('Double-Stitched Belt',       'double-stitched-belt',       'belts', 1, '100.00',
     'Signature double-stitch detail along the edges. Made from 4mm thick premium cowhide.',
     ['S','M','L','XL'], 5, 'belt5.jpg'),
    ('Embossed Pattern Belt',      'embossed-pattern-belt',      'belts', 2, '125.00',
     'Traditional Azerbaijani embossed pattern pressed into full-grain leather. Unique collector piece.',
     ['S','M','L','XL'], 4, 'belt6.jpg'),
    ('Casual Everyday Belt',       'casual-everyday-belt',       'belts', 0, '75.00',
     'Durable everyday belt in waxed leather. Water-resistant finish, brushed nickel hardware.',
     ['S','M','L','XL'], 10, 'belt7.jpg'),
    ('Formal Dress Belt',          'formal-dress-belt',          'belts', 1, '135.00',
     'Ultra-slim dress belt in patent leather. Perfect for formal occasions and business attire.',
     ['S','M','L','XL'], 4, 'belt8.jpg'),
    ('Vintage Buckle Belt',        'vintage-buckle-belt',        'belts', 2, '115.00',
     'Vintage-style roller buckle paired with aged tan leather. Each piece is uniquely distressed.',
     ['S','M','L','XL'], 5, 'belt9.jpg'),
    ('Contrast Stitch Belt',       'contrast-stitch-belt',       'belts', 0, '90.00',
     'Dark brown leather with cream contrast stitching. Eye-catching detail that elevates any outfit.',
     ['S','M','L','XL'], 6, 'belt10.jpg'),

    # ── BAGS ───────────────────────────────────────────────────────────
    ('Leather Tote Bag',           'leather-tote-bag',           'bags',  1, '280.00',
     'Spacious full-grain leather tote with interior pockets and a sturdy base. Ideal for work or travel.',
     ['Standard'], 5, 'bag1.jpg'),
    ('Crossbody Satchel',          'crossbody-satchel',          'bags',  2, '220.00',
     'Compact crossbody satchel with adjustable strap and magnetic clasp. Holds phone, wallet and keys.',
     ['Standard'], 6, 'bag2.jpg'),
    ('Leather Shoulder Bag',       'leather-shoulder-bag',       'bags',  0, '310.00',
     'Structured shoulder bag in vegetable-tanned leather. Three internal compartments, brass hardware.',
     ['Standard'], 4, 'bag3.jpg'),
    ('Mini Clutch Bag',            'mini-clutch-bag',            'bags',  1, '175.00',
     'Elegant mini clutch in smooth calfskin. Detachable chain strap, slip pockets inside.',
     ['Standard'], 7, 'bag4.jpg'),
    ('Weekend Holdall',            'weekend-holdall',            'bags',  2, '380.00',
     'Generous weekender bag in waxed leather. Water-resistant, reinforced handles, shoulder strap included.',
     ['Standard'], 3, 'bag5.jpg'),

    # ── BOOTS ──────────────────────────────────────────────────────────
    ('Classic Chelsea Boots',      'classic-chelsea-boots',      'boots', 0, '395.00',
     'Hand-lasted Chelsea boots in full-grain leather. Elastic side panels, leather lining.',
     ['38','39','40','41','42','43','44'], 4, 'boot1.jpg'),
    ('Rugged Work Boots',          'rugged-work-boots',          'boots', 1, '420.00',
     'Heavyweight work boots with Goodyear welt construction. Oil-resistant rubber sole.',
     ['38','39','40','41','42','43','44'], 3, 'boot3.jpg'),
    ('Ankle Leather Boots',        'ankle-leather-boots',        'boots', 2, '360.00',
     'Sleek ankle boots in smooth calfskin with a stacked wooden heel. Fully leather-lined.',
     ['37','38','39','40','41','42'], 5, 'boot4.jpg'),
    ('Riding Style Boots',         'riding-style-boots',         'boots', 0, '450.00',
     'Tall riding-inspired boots in vegetable-tanned leather. Pull-on design with inside zip.',
     ['37','38','39','40','41','42'], 3, 'boot5.jpg'),
    ('Desert Chukka Boots',        'desert-chukka-boots',        'boots', 1, '310.00',
     'Lightweight chukka boots in suede-finished leather. Two-eyelet lace-up closure, crepe sole.',
     ['38','39','40','41','42','43'], 6, 'boot6.jpg'),

    # ── SHOES ──────────────────────────────────────────────────────────
    ('Oxford Dress Shoes',         'oxford-dress-shoes',         'shoes', 2, '340.00',
     'Cap-toe Oxford in mirror-polished calf leather. Blake-stitched construction, leather sole.',
     ['38','39','40','41','42','43','44'], 4, 'shoe1.jpg'),
    ('Leather Loafers',            'leather-loafers',            'shoes', 0, '290.00',
     'Penny loafers in buttery soft nappa leather. Flexible rubber sole, hand-sewn moccasin welt.',
     ['38','39','40','41','42','43'], 5, 'shoe2.jpg'),
    ('Derby Brogue Shoes',         'derby-brogue-shoes',         'shoes', 1, '320.00',
     'Full-brogue Derby in pebble-grain leather. Dainite rubber sole for all-weather wear.',
     ['38','39','40','41','42','43','44'], 4, 'shoe3.jpg'),
    ('Leather Monk Strap',         'leather-monk-strap',         'shoes', 2, '355.00',
     'Double monk-strap in polished calf leather. Gold-tone hardware, leather-lined interior.',
     ['38','39','40','41','42','43'], 3, 'shoe4.jpg'),
    ('Casual Leather Sneakers',    'casual-leather-sneakers',    'shoes', 0, '255.00',
     'Minimalist leather sneakers with cushioned insole. Vulcanised rubber sole, easy-clean finish.',
     ['38','39','40','41','42','43','44','45'], 6, 'shoe5.jpg'),

    # ── JACKETS ────────────────────────────────────────────────────────
    ('Biker Leather Jacket',       'biker-leather-jacket',       'jackets', 1, '750.00',
     'Classic asymmetric biker jacket in premium cowhide. Quilted lining, multiple pockets.',
     ['S','M','L','XL','XXL'], 3, 'jacket1.jpg'),
    ('Slim Fit Leather Jacket',    'slim-fit-leather-jacket',    'jackets', 2, '690.00',
     'Tailored slim-fit jacket in supple lambskin. Clean zip-front design, fully silk-lined.',
     ['S','M','L','XL'], 3, 'jacket2.jpg'),
    ('Aviator Leather Jacket',     'aviator-leather-jacket',     'jackets', 0, '820.00',
     'A-2 aviator jacket in washed horsehide. Ribbed collar and cuffs, knit waistband.',
     ['S','M','L','XL','XXL'], 2, 'jacket3.jpg'),
    ('Vintage Racer Jacket',       'vintage-racer-jacket',       'jackets', 1, '670.00',
     'Cafe-racer inspired jacket in aged tan leather. Minimal hardware, stand-up collar.',
     ['S','M','L','XL'], 3, 'jacket4.jpg'),
    ('Long Leather Coat',          'long-leather-coat',          'jackets', 2, '980.00',
     'Full-length leather overcoat in smooth calfskin. Double-breasted, notched lapel, belt.',
     ['S','M','L','XL'], 2, 'jacket5.jpg'),
    ('Perforated Leather Jacket',  'perforated-leather-jacket',  'jackets', 0, '680.00',
     'Perforated leather jacket for breathability. YKK zippers, four exterior pockets.',
     ['S','M','L','XL'], 3, 'jacket6.jpg'),
    ('Military Field Jacket',      'military-field-jacket',      'jackets', 1, '720.00',
     'Military-inspired field jacket in waxed leather. Cargo pockets, epaulettes, corduroy collar.',
     ['S','M','L','XL','XXL'], 3, 'jacket7.jpg'),

    # ── HATS ───────────────────────────────────────────────────────────
    ('Classic Fedora',             'classic-fedora',             'hats',  2, '145.00',
     'Hand-shaped fedora in supple leather. Grosgrain ribbon band, pinched crown.',
     ['S','M','L'], 6, 'hat1.png'),
    ('Wide Brim Hat',              'wide-brim-hat',              'hats',  0, '160.00',
     'Wide-brim hat in vegetable-tanned leather. UV-resistant finish, adjustable inner band.',
     ['S','M','L'], 5, 'hat2.png'),
    ('Leather Cap',                'leather-cap',                'hats',  1, '110.00',
     'Six-panel structured cap in smooth calfskin. Adjustable snap-back closure.',
     ['Standard'], 8, 'hat3.png'),
    ('Flat Cap',                   'leather-flat-cap',           'hats',  2, '120.00',
     'Traditional flat cap in herringbone-embossed leather. Fully cotton-lined interior.',
     ['Standard'], 7, 'hat4.png'),
    ('Bucket Hat',                 'leather-bucket-hat',         'hats',  0, '95.00',
     'Casual bucket hat in washed leather. Lightweight construction, breathable lining.',
     ['S','M','L'], 9, 'hat5.png'),

    # ── WALLETS ────────────────────────────────────────────────────────
    ('Bifold Card Wallet',         'bifold-card-wallet',         'wallets', 1, '65.00',
     'Slim bifold wallet in full-grain leather. 6 card slots, note compartment, RFID blocking.',
     ['Standard'], 12, 'wallet1.jpg'),
    ('Trifold Leather Wallet',     'trifold-leather-wallet',     'wallets', 2, '80.00',
     'Classic trifold with 12 card slots and a zip coin pocket. Compact profile.',
     ['Standard'], 10, 'wallet2.jpg'),
    ('Zip-Around Wallet',          'zip-around-wallet',          'wallets', 0, '95.00',
     'Full-zip wallet in smooth calfskin. 8 card slots, multiple note sections, coin pocket.',
     ['Standard'], 8, 'wallet3.jpg'),
    ('Minimalist Cardholder',      'minimalist-cardholder',      'wallets', 1, '45.00',
     'Ultra-slim cardholder for 4–6 cards. Push-through slot for quick access. No bulk.',
     ['Standard'], 15, 'wallet4.jpg'),
    ('Long Leather Wallet',        'long-leather-wallet',        'wallets', 2, '110.00',
     'Continental-style wallet in vegetable-tanned leather. 12 card slots, flat note section.',
     ['Standard'], 7, 'wallet5.jpg'),
    ('Coin Purse Wallet',          'coin-purse-wallet',          'wallets', 0, '55.00',
     'Traditional coin purse with card slots and a bill compartment. Brass snap closure.',
     ['Standard'], 10, 'wallet6.jpg'),
    ('Passport Wallet',            'passport-wallet',            'wallets', 1, '85.00',
     'Travel wallet holding a passport, boarding pass, cards and cash. RFID-shielded lining.',
     ['Standard'], 8, 'wallet7.jpg'),

    # ── BRACELETS ──────────────────────────────────────────────────────
    ('Braided Leather Bracelet',   'braided-leather-bracelet',   'bracelets', 2, '45.00',
     'Hand-braided leather bracelet with a sterling silver clasp. Adjustable sizing.',
     ['S','M','L'], 15, 'bracelet1.jpg'),
    ('Wrap Leather Bracelet',      'wrap-leather-bracelet',      'bracelets', 0, '55.00',
     'Three-wrap bracelet in waxed leather cord. Magnetic clasp, unisex design.',
     ['Standard'], 12, 'bracelet2.jpg'),
    ('Cuff Bracelet',              'leather-cuff-bracelet',      'bracelets', 1, '65.00',
     'Wide leather cuff with embossed geometric pattern. Snap-button fastening.',
     ['S','M','L'], 10, 'bracelet3.jpg'),
    ('Beaded Leather Bracelet',    'beaded-leather-bracelet',    'bracelets', 2, '50.00',
     'Leather cord bracelet with hand-carved wooden beads. Tied fastening, adjustable.',
     ['Standard'], 12, 'bracelet4.jpg'),
    ('Stacked Bracelet Set',       'stacked-bracelet-set',       'bracelets', 0, '75.00',
     'Set of three complementary bracelets — braided, flat and beaded — designed to stack.',
     ['S','M','L'], 8, 'bracelet5.jpg'),
]


class Command(BaseCommand):
    help = 'Seed database with products and upload images to Cloudinary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--images-dir',
            type=str,
            default=None,
            help='Path to folder with product images (default: ../project pictures/)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing products before seeding',
        )

    def handle(self, *args, **options):
        images_dir = options['images_dir']
        if not images_dir:
            images_dir = os.path.join(settings.BASE_DIR, '..', 'project pictures')
        images_dir = os.path.abspath(images_dir)

        if not os.path.isdir(images_dir):
            self.stderr.write(f'Images dir not found: {images_dir}')
            self.stderr.write('Pass --images-dir "path/to/project pictures"')
            return

        if options['clear']:
            Product.objects.all().delete()
            self.stdout.write('Cleared existing products.')

        # ── Categories ────────────────────────────────────────────────
        self.stdout.write('Creating categories...')
        cat_objects = {}
        for slug, (parent_slug, name) in CATEGORIES.items():
            parent = cat_objects.get(parent_slug)
            obj, created = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'parent': parent},
            )
            if not created and obj.parent != parent:
                obj.parent = parent
                obj.save()
            cat_objects[slug] = obj
            if created:
                self.stdout.write(f'  + Category: {name}')

        # ── Artisans ──────────────────────────────────────────────────
        self.stdout.write('Creating artisans...')
        artisan_objects = []
        for data in ARTISANS:
            obj, created = Artisan.objects.get_or_create(
                name=data['name'],
                defaults={'region': data['region'], 'description': data['description']},
            )
            artisan_objects.append(obj)
            if created:
                self.stdout.write(f'  + Artisan: {data["name"]}')

        # ── Products ──────────────────────────────────────────────────
        self.stdout.write('Creating products...')
        created_count = 0
        skipped_count = 0

        for (name, slug, cat_slug, art_idx,
             price, description, sizes, stock, image_file) in PRODUCTS:

            if Product.objects.filter(slug=slug).exists():
                skipped_count += 1
                continue

            category = cat_objects[cat_slug]
            artisan = artisan_objects[art_idx]

            product = Product(
                category=category,
                artisan=artisan,
                name=name,
                slug=slug,
                description=description,
                price=Decimal(price),
                is_available=True,
                stock=0,
            )

            # Upload image
            image_path = os.path.join(images_dir, image_file)
            if os.path.isfile(image_path):
                with open(image_path, 'rb') as f:
                    product.image.save(image_file, File(f), save=False)
                self.stdout.write(f'  ✓ {name} (with image)')
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ! {name} (no image: {image_file})')
                )

            product.save()

            # ── Variants ──────────────────────────────────────────────
            for size in sizes:
                ProductVariant.objects.get_or_create(
                    product=product,
                    size=size,
                    defaults={'stock': stock},
                )

            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count} products, skipped {skipped_count} (already exist).'
        ))
