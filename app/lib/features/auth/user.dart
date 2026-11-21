enum UserRole { tenant, owner, admin }

class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    required this.phone,
    required this.isIdentityVerified,
  });

  final int id;
  final String email;
  final String firstName;
  final String lastName;
  final UserRole role;
  final String phone;
  final bool isIdentityVerified;

  String get fullName => '$firstName $lastName'.trim();

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as int,
        email: json['email'] as String,
        firstName: (json['first_name'] ?? '') as String,
        lastName: (json['last_name'] ?? '') as String,
        role: UserRole.values.byName(json['role'] as String),
        phone: (json['phone'] ?? '') as String,
        isIdentityVerified: (json['is_identity_verified'] ?? false) as bool,
      );
}
