# users/management/commands/populate_events.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from burnermanagement.firebase_config import get_firestore_client
from venues.models import Venue
from datetime import datetime, timedelta
import random
import uuid

class Command(BaseCommand):
    help = 'Populate Firestore with sample events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of events to create (default: 20)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing events before creating new ones'
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting event population...')
        
        db = get_firestore_client()
        if not db:
            self.stdout.write(
                self.style.ERROR('Failed to connect to Firestore. Check your Firebase configuration.')
            )
            return

        # Get venues first
        venues = Venue.get_all_active()
        if not venues:
            self.stdout.write(
                self.style.ERROR('No venues found. Please create venues first.')
            )
            return

        # Clear existing events if requested
        if options['clear']:
            self.clear_events(db)

        # Create events
        count = options['count']
        self.create_events(db, venues, count)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} events!')
        )

    def clear_events(self, db):
        """Clear all existing events"""
        self.stdout.write('Clearing existing events...')
        try:
            events_ref = db.collection('events')
            events = events_ref.stream()
            
            deleted_count = 0
            for event in events:
                event.reference.delete()
                deleted_count += 1
            
            self.stdout.write(f'Deleted {deleted_count} existing events')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error clearing events: {e}')
            )

    def create_events(self, db, venues, count):
        """Create sample events"""
        
        # Real London & Nottingham venues with realistic events
        venue_specific_events = {
            # London venues
            'fabric': [
                {
                    'name': 'fabric Presents: Nina Kraviz',
                    'description': 'The Russian techno queen returns to fabric with her hypnotic blend of acid and experimental electronic music.',
                    'imageUrl': 'https://images.unsplash.com/photo-1571266028243-d220c6cd3ba7?w=800&h=600&fit=crop',
                    'price_range': (25.0, 35.0),
                },
                {
                    'name': 'WetYourSelf! with Honey Dijon',
                    'description': 'Deep house royalty Honey Dijon brings her signature Chicago sound to fabric\'s legendary sound system.',
                    'imageUrl': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=600&fit=crop',
                    'price_range': (20.0, 30.0),
                },
                {
                    'name': 'fabriclive: Andy C All Night Long',
                    'description': 'Drum & bass legend Andy C takes over the decks for an unmissable all-night journey through jungle and D&B.',
                    'imageUrl': 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=800&h=600&fit=crop',
                    'price_range': (30.0, 40.0),
                }
            ],
            'Ministry of Sound': [
                {
                    'name': 'The Gallery: Carl Cox & Friends',
                    'description': 'Techno titan Carl Cox brings his legendary energy to The Gallery with special guests.',
                    'imageUrl': 'https://images.unsplash.com/photo-1571266028243-d220c6cd3ba7?w=800&h=600&fit=crop',
                    'price_range': (35.0, 45.0),
                },
                {
                    'name': 'Hed Kandi: House Heaven',
                    'description': 'The ultimate house music experience with resident DJs and special international guests.',
                    'imageUrl': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=600&fit=crop',
                    'price_range': (25.0, 35.0),
                },
                {
                    'name': 'Ministry Sessions: Tale Of Us',
                    'description': 'Italian melodic techno masters Tale Of Us deliver their signature emotional electronic journey.',
                    'imageUrl': 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=800&h=600&fit=crop',
                    'price_range': (30.0, 40.0),
                }
            ],
            'Corsica Studios': [
                {
                    'name': 'WHYTE HRSE: Objekt Live',
                    'description': 'Cutting-edge electronic producer Objekt brings his innovative live show to Corsica\'s intimate setting.',
                    'imageUrl': 'https://images.unsplash.com/photo-1516873240891-4bbac3eca2c9?w=800&h=600&fit=crop',
                    'price_range': (18.0, 25.0),
                },
                {
                    'name': 'Infinite Machine: Machine Girl',
                    'description': 'Breakcore chaos meets digital hardcore in this intense underground electronic showcase.',
                    'imageUrl': 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=800&h=600&fit=crop',
                    'price_range': (15.0, 22.0),
                },
                {
                    'name': 'Livity Sound: Peverelist',
                    'description': 'Bristol dubstep pioneer Peverelist explores the deeper realms of UK bass music.',
                    'imageUrl': 'https://images.unsplash.com/photo-1571266028243-d220c6cd3ba7?w=800&h=600&fit=crop',
                    'price_range': (16.0, 24.0),
                }
            ],
            'XOYO': [
                {
                    'name': 'XOYO Presents: Charlotte de Witte',
                    'description': 'Belgian techno sensation Charlotte de Witte delivers her dark, driving sound to XOYO\'s immersive dancefloor.',
                    'imageUrl': 'https://images.unsplash.com/photo-1571266028243-d220c6cd3ba7?w=800&h=600&fit=crop',
                    'price_range': (28.0, 38.0),
                },
                {
                    'name': 'London Elektricity Big Band Live',
                    'description': 'Hospital Records\' jazzstep innovators bring their full live band experience to XOYO.',
                    'imageUrl': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=600&fit=crop',
                    'price_range': (25.0, 35.0),
                }
            ],
            'Village Underground': [
                {
                    'name': 'Secretsundaze: Move D',
                    'description': 'German minimal house master Move D curates an evening of deep, hypnotic grooves.',
                    'imageUrl': 'https://images.unsplash.com/photo-1516873240891-4bbac3eca2c9?w=800&h=600&fit=crop',
                    'price_range': (20.0, 28.0),
                },
                {
                    'name': 'Futureboogie: Mall Grab',
                    'description': 'Australian lo-fi house producer Mall Grab brings his signature vintage sound to East London.',
                    'imageUrl': 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=800&h=600&fit=crop',
                    'price_range': (22.0, 30.0),
                }
            ],
            
            # Nottingham venues
            'Stealth': [
                {
                    'name': 'Stealth Sessions: Ben Klock',
                    'description': 'Berghain resident Ben Klock brings his uncompromising techno sound to Nottingham\'s underground.',
                    'imageUrl': 'https://images.unsplash.com/photo-1571266028243-d220c6cd3ba7?w=800&h=600&fit=crop',
                    'price_range': (25.0, 35.0),
                },
                {
                    'name': 'Bass Culture: Skepta',
                    'description': 'Grime legend Skepta takes over Stealth for a night of UK bass and underground energy.',
                    'imageUrl': 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=800&h=600&fit=crop',
                    'price_range': (30.0, 40.0),
                },
                {
                    'name': 'Detonate: Sub Focus',
                    'description': 'Drum & bass heavyweight Sub Focus delivers his signature anthemic sound to the Stealth faithful.',
                    'imageUrl': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=600&fit=crop',
                    'price_range': (28.0, 38.0),
                }
            ],
            'Rescue Rooms': [
                {
                    'name': 'Leftfoot: Four Tet Live',
                    'description': 'Electronic innovator Four Tet presents his acclaimed live show featuring organic beats and ethereal melodies.',
                    'imageUrl': 'https://images.unsplash.com/photo-1516873240891-4bbac3eca2c9?w=800&h=600&fit=crop',
                    'price_range': (30.0, 40.0),
                },
                {
                    'name': 'Bodega Social: Bicep DJ Set',
                    'description': 'Belfast duo Bicep deliver their nostalgic blend of house, breakbeat and electronica.',
                    'imageUrl': 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=800&h=600&fit=crop',
                    'price_range': (25.0, 35.0),
                }
            ],
            'NG1': [
                {
                    'name': 'Nottingham Bass Collective: Goldie',
                    'description': 'Jungle pioneer Goldie returns to his Midlands roots with classic and contemporary drum & bass.',
                    'imageUrl': 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=800&h=600&fit=crop',
                    'price_range': (22.0, 32.0),
                },
                {
                    'name': 'Eastern Electrics: Fisher',
                    'description': 'Australian tech house phenomenon Fisher brings his viral energy to Nottingham.',
                    'imageUrl': 'https://images.unsplash.com/photo-1571266028243-d220c6cd3ba7?w=800&h=600&fit=crop',
                    'price_range': (25.0, 35.0),
                }
            ]
        }
        
        # Additional generic events for any venue
        generic_events = [
            {
                'name': 'Underground Collective: Local Heroes',
                'description': 'Showcasing the finest underground electronic talent from the local scene.',
                'imageUrl': 'https://images.unsplash.com/photo-1516873240891-4bbac3eca2c9?w=800&h=600&fit=crop',
                'price_range': (10.0, 18.0),
            },
            {
                'name': 'Late Night Sessions',
                'description': 'An intimate late-night journey through deep house and minimal techno.',
                'imageUrl': 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=800&h=600&fit=crop',
                'price_range': (15.0, 25.0),
            },
            {
                'name': 'Digital Basement: Bass Explorers',
                'description': 'Exploring the depths of UK bass culture with emerging and established artists.',
                'imageUrl': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=800&h=600&fit=crop',
                'price_range': (12.0, 20.0),
            }
        ]

        created_count = 0
        now = datetime.utcnow()

        for i in range(count):
            try:
                # Choose a random venue
                venue = random.choice(venues)
                
                # Try to find venue-specific events first, otherwise use generic
                available_events = venue_specific_events.get(venue.name, [])
                if not available_events:
                    # Check partial matches for common venue names
                    for venue_key in venue_specific_events.keys():
                        if venue_key.lower() in venue.name.lower() or venue.name.lower() in venue_key.lower():
                            available_events = venue_specific_events[venue_key]
                            break
                
                # If no specific events found, use generic events
                if not available_events:
                    available_events = generic_events
                
                # Choose a random event template
                template = random.choice(available_events)
                
                # Generate event data
                event_id = str(uuid.uuid4())
                
                # Random date between 7 days and 120 days from now (typical booking window)
                days_ahead = random.randint(7, 120)
                event_date = now + timedelta(days=days_ahead)
                
                # Electronic music events typically start later
                hour = random.randint(21, 23)  # 9 PM to 11 PM start times
                minute = random.choice([0, 30])  # On the hour or half hour
                event_date = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Ensure it's a Friday or Saturday for club events
                weekday = event_date.weekday()
                if weekday not in [4, 5]:  # If not Friday or Saturday
                    days_to_add = (4 - weekday) % 7  # Days to next Friday
                    if days_to_add == 0:
                        days_to_add = 7  # Next Friday if today is Friday
                    event_date += timedelta(days=days_to_add)
                
                # Generate realistic pricing and capacity based on venue
                price = round(random.uniform(*template['price_range']), 2)
                
                # Set capacity based on venue size (realistic club capacities)
                venue_capacities = {
                    'fabric': (1500, 2500),
                    'Ministry of Sound': (1000, 1800),
                    'XOYO': (400, 800),
                    'Corsica Studios': (200, 400),
                    'Village Underground': (300, 600),
                    'Stealth': (800, 1200),
                    'Rescue Rooms': (400, 650),
                    'NG1': (300, 500)
                }
                
                # Find capacity for this venue
                capacity_range = None
                for venue_key, capacity in venue_capacities.items():
                    if venue_key.lower() in venue.name.lower():
                        capacity_range = capacity
                        break
                
                # Default capacity if venue not found
                if not capacity_range:
                    capacity_range = (200, 800)
                
                max_tickets = random.randint(*capacity_range)
                
                # Electronic events typically sell better - 20% to 90% sold
                tickets_sold = random.randint(int(max_tickets * 0.2), int(max_tickets * 0.9))
                
                # Add date suffix for uniqueness if needed
                date_suffix = event_date.strftime("%d.%m")
                event_name = template['name']
                
                # Add date for uniqueness on subsequent iterations
                if i > len(available_events):
                    event_name += f" [{date_suffix}]"

                # Higher chance of being featured for bigger artists/venues
                featured_venues = ['fabric', 'Ministry of Sound', 'Stealth']
                is_featured_chance = 0.4 if any(fv.lower() in venue.name.lower() for fv in featured_venues) else 0.15
                is_featured = random.random() < is_featured_chance

                event_data = {
                    'name': event_name,
                    'description': template['description'],
                    'venue': venue.name,
                    'venueId': venue.id,
                    'date': event_date,
                    'price': price,
                    'maxTickets': max_tickets,
                    'ticketsSold': tickets_sold,
                    'imageUrl': template['imageUrl'],
                    'isFeatured': is_featured,
                    'createdAt': now,
                    'createdBy': 'admin-script',
                    'isActive': True
                }

                # Save to Firestore
                db.collection('events').document(event_id).set(event_data)
                
                created_count += 1
                
                # Print progress
                if created_count % 5 == 0:
                    self.stdout.write(f'Created {created_count}/{count} events...')

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error creating event {i+1}: {e}')
                )

        self.stdout.write(f'Successfully created {created_count} events')

        # Show some stats
        self.show_stats(db, venues)

    def show_stats(self, db, venues):
        """Show statistics about created events"""
        try:
            events_ref = db.collection('events')
            events = list(events_ref.stream())
            
            total_events = len(events)
            featured_events = sum(1 for event in events if event.to_dict().get('isFeatured', False))
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write('EVENT STATISTICS')
            self.stdout.write('='*50)
            self.stdout.write(f'Total Events: {total_events}')
            self.stdout.write(f'Featured Events: {featured_events}')
            self.stdout.write(f'Available Venues: {len(venues)}')
            
            # Events per venue
            venue_counts = {}
            for event in events:
                event_data = event.to_dict()
                venue_id = event_data.get('venueId', 'Unknown')
                venue_name = event_data.get('venue', 'Unknown')
                venue_counts[venue_name] = venue_counts.get(venue_name, 0) + 1
            
            self.stdout.write('\nEvents per venue:')
            for venue_name, count in venue_counts.items():
                self.stdout.write(f'  {venue_name}: {count} events')
            
            self.stdout.write('='*50)
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error showing stats: {e}')
            )