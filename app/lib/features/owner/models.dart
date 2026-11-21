/// Libellés français des valeurs renvoyées par l'API.
const propertyTypes = {
  'studio': 'Studio',
  'room': 'Chambre',
  'apartment': 'Appartement',
  'house': 'Maison',
  'villa': 'Villa',
};

const propertyStatuses = {
  'draft': 'Brouillon',
  'pending': 'En attente de validation',
  'published': 'Publiée',
  'rejected': 'Refusée',
  'suspended': 'Suspendue',
};

class Room {
  const Room({
    required this.id,
    required this.roomType,
    required this.name,
    required this.isExterior,
    required this.order,
    required this.panoramaStatus,
    required this.photosCount,
  });

  final int id;
  final String roomType;
  final String name;
  final bool isExterior;
  final int order;
  final String panoramaStatus;
  final int photosCount;

  factory Room.fromJson(Map<String, dynamic> j) => Room(
        id: j['id'] as int,
        roomType: j['room_type'] as String,
        name: j['name'] as String,
        isExterior: (j['is_exterior'] ?? false) as bool,
        order: (j['order'] ?? 0) as int,
        panoramaStatus: (j['panorama_status'] ?? 'none') as String,
        photosCount: (j['photos_count'] ?? 0) as int,
      );
}

class OwnerProperty {
  const OwnerProperty({
    required this.id,
    required this.propertyType,
    required this.title,
    required this.neighborhood,
    required this.city,
    required this.rent,
    required this.status,
    required this.rejectionReason,
    required this.suspendedByAdmin,
    required this.entrancePhoto,
    required this.rooms,
  });

  final int id;
  final String propertyType;
  final String title;
  final String neighborhood;
  final String city;
  final int rent;
  final String status;
  final String rejectionReason;
  final bool suspendedByAdmin;
  final String? entrancePhoto;
  final List<Room> rooms;

  bool get isEditablePlan => status == 'draft' || status == 'rejected';
  String get statusLabel => propertyStatuses[status] ?? status;

  factory OwnerProperty.fromJson(Map<String, dynamic> j) => OwnerProperty(
        id: j['id'] as int,
        propertyType: j['property_type'] as String,
        title: j['title'] as String,
        neighborhood: (j['neighborhood'] ?? '') as String,
        city: (j['city'] ?? '') as String,
        rent: (j['rent'] ?? 0) as int,
        status: j['status'] as String,
        rejectionReason: (j['rejection_reason'] ?? '') as String,
        suspendedByAdmin: (j['suspended_by_admin'] ?? false) as bool,
        entrancePhoto: j['entrance_photo'] as String?,
        rooms: [
          for (final r in (j['rooms'] as List? ?? const []))
            Room.fromJson(r as Map<String, dynamic>),
        ],
      );
}

/// Réponses aux questions de l'assistant (envoyées à /room-plan/).
class RoomPlanAnswers {
  int bedrooms = 1;
  bool livingRoom = true;
  String kitchen = 'interior';
  String bathroom = 'interior';
  String toilet = 'with_bathroom';
  bool balcony = false;
  bool terrace = false;
  bool yard = false;
  List<String> others = [];

  Map<String, dynamic> toJson() => {
        'bedrooms': bedrooms,
        'living_room': livingRoom,
        'kitchen': kitchen,
        'bathroom': bathroom,
        'toilet': bathroom == 'none' && toilet == 'with_bathroom' ? 'none' : toilet,
        'balcony': balcony,
        'terrace': terrace,
        'yard': yard,
        'others': others,
      };
}

/// Montant en francs CFA, avec espaces entre les milliers : 75 000 FCFA.
String formatXof(int amount) {
  final digits = amount.toString();
  final buffer = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buffer.write(' ');
    buffer.write(digits[i]);
  }
  return '$buffer FCFA';
}
