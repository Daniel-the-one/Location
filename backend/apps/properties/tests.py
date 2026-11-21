import io
import shutil
import tempfile

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image
from rest_framework.test import APITestCase

from apps.accounts.models import IdentityVerification, User
from apps.exchanges.models import Notification

from . import services
from .models import Property, Room
from .room_plan import build_room_plan, main_rooms_count

TMP_MEDIA = tempfile.mkdtemp()
PASSWORD = "Lome-2026-secure"


def jpeg(name="photo.jpg", size=(2400, 1800)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (120, 160, 200)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def make_owner(email="o@example.com", verified=True):
    owner = User.objects.create_user(email=email, password=PASSWORD, role=User.Role.OWNER)
    if verified:
        IdentityVerification.objects.create(
            user=owner, document="identity/x.pdf", status=IdentityVerification.Status.APPROVED
        )
    return owner


def make_property(owner, **extra):
    data = dict(
        owner=owner,
        property_type="apartment",
        title="Appartement à Bè",
        address="Rue 12",
        neighborhood="Bè",
        city="Lomé",
        rent=75000,
    )
    data.update(extra)
    return Property.objects.create(**data)


class RoomPlanTests(SimpleTestCase):
    def names(self, **answers):
        base = dict(bedrooms=0, living_room=False, kitchen="none", bathroom="none", toilet="none")
        base.update(answers)
        return [r.name for r in build_room_plan(base)]

    def test_typical_apartment_order(self):
        self.assertEqual(
            self.names(
                bedrooms=2, living_room=True, kitchen="interior", bathroom="interior",
                toilet="with_bathroom", balcony=True,
            ),
            ["Salon", "Chambre 1", "Chambre 2", "Cuisine", "Douche et WC", "Balcon"],
        )

    def test_exterior_spaces_come_last_with_yard_first(self):
        self.assertEqual(
            self.names(
                bedrooms=1, living_room=True, kitchen="exterior", bathroom="exterior",
                toilet="exterior", yard=True,
            ),
            ["Salon", "Chambre", "Cour", "Cuisine (extérieur)", "Douche (extérieur)",
             "WC (extérieur)"],
        )

    def test_studio_gets_main_room(self):
        self.assertEqual(self.names(bathroom="interior", toilet="with_bathroom"),
                         ["Pièce principale", "Douche et WC"])

    def test_other_rooms_and_count(self):
        plan = build_room_plan(dict(bedrooms=3, living_room=True, kitchen="interior",
                                    bathroom="interior", toilet="interior", others=["Bureau"]))
        self.assertIn("Bureau", [r.name for r in plan])
        self.assertEqual(main_rooms_count(plan), 4)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class OwnerFlowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.owner = make_owner()
        self.client.force_authenticate(self.owner)

    def create_property(self):
        res = self.client.post("/api/owner/properties/", {
            "property_type": "apartment", "title": "Appartement à Bè", "address": "Rue 12",
            "neighborhood": "Bè", "city": "Lomé", "rent": 75000, "deposit": 150000,
            "amenities": ["Eau", "Électricité"],
        }, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        return res.data["id"]

    def apply_plan(self, pid):
        return self.client.post(f"/api/owner/properties/{pid}/room-plan/", {
            "bedrooms": 1, "living_room": True, "kitchen": "interior",
            "bathroom": "interior", "toilet": "with_bathroom",
        }, format="json")

    def test_full_creation_flow_until_submission(self):
        pid = self.create_property()
        res = self.apply_plan(pid)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r["name"] for r in res.data["rooms"]],
                         ["Salon", "Chambre", "Cuisine", "Douche et WC"])
        self.assertEqual(res.data["rooms_count"], 2)

        # Soumission refusée tant qu'il manque la porte et les photos
        res = self.client.post(f"/api/owner/properties/{pid}/submit/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(res.data["errors"]), 2)

        res = self.client.post(f"/api/owner/properties/{pid}/entrance-photo/",
                               {"image": jpeg()}, format="multipart")
        self.assertEqual(res.status_code, 200)
        room_ids = [r["id"] for r in res.data["rooms"]]
        for rid in room_ids:
            res = self.client.post(f"/api/owner/rooms/{rid}/photos/",
                                   {"images": [jpeg("a.jpg"), jpeg("b.jpg")]}, format="multipart")
            self.assertEqual(res.status_code, 201, res.data)
            self.assertEqual(res.data["photos_count"], 2)
            self.assertEqual(res.data["panorama_status"], "pending")

        res = self.client.post(f"/api/owner/properties/{pid}/submit/")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["status"], "pending")

    def test_photos_are_resized_to_1600px(self):
        pid = self.create_property()
        self.apply_plan(pid)
        room = Room.objects.filter(property_id=pid).first()
        self.client.post(f"/api/owner/rooms/{room.id}/photos/", {"images": [jpeg()]},
                         format="multipart")
        with Image.open(room.photos.first().image.path) as img:
            self.assertEqual(max(img.size), 1600)

    def test_non_image_rejected(self):
        pid = self.create_property()
        self.apply_plan(pid)
        room = Room.objects.filter(property_id=pid).first()
        fake = SimpleUploadedFile("x.jpg", b"not an image", content_type="image/jpeg")
        res = self.client.post(f"/api/owner/rooms/{room.id}/photos/", {"images": [fake]},
                               format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_reorder_rooms(self):
        pid = self.create_property()
        ids = [r["id"] for r in self.apply_plan(pid).data["rooms"]]
        res = self.client.post(f"/api/owner/properties/{pid}/reorder-rooms/",
                               {"room_ids": list(reversed(ids))}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r["id"] for r in res.data["rooms"]], list(reversed(ids)))
        bad = self.client.post(f"/api/owner/properties/{pid}/reorder-rooms/",
                               {"room_ids": ids[:2]}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_delete_room_renumbers(self):
        pid = self.create_property()
        ids = [r["id"] for r in self.apply_plan(pid).data["rooms"]]
        self.assertEqual(self.client.delete(f"/api/owner/rooms/{ids[0]}/").status_code, 204)
        self.assertEqual(list(Room.objects.filter(property_id=pid).values_list("order", flat=True)),
                         [0, 1, 2])

    def test_unverified_owner_cannot_submit(self):
        other = make_owner("new@example.com", verified=False)
        self.client.force_authenticate(other)
        pid = self.create_property()
        res = self.client.post(f"/api/owner/properties/{pid}/submit/")
        self.assertEqual(res.status_code, 400)
        self.assertIn("identité", res.data["errors"][0])

    def test_owner_cannot_touch_someone_elses_property(self):
        prop = make_property(make_owner("other@example.com"))
        self.assertEqual(self.client.get(f"/api/owner/properties/{prop.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/owner/properties/{prop.id}/").status_code, 404)

    def test_tenant_cannot_use_owner_api(self):
        tenant = User.objects.create_user(email="t@example.com", password=PASSWORD)
        self.client.force_authenticate(tenant)
        self.assertEqual(self.client.get("/api/owner/properties/").status_code, 403)

    def test_owner_suspend_and_reactivate_but_not_after_admin_suspension(self):
        prop = make_property(self.owner, status=Property.Status.PUBLISHED)
        self.assertEqual(self.client.post(f"/api/owner/properties/{prop.id}/suspend/").status_code,
                         200)
        res = self.client.post(f"/api/owner/properties/{prop.id}/reactivate/")
        self.assertEqual(res.data["status"], "published")
        services.admin_suspend_property(prop, "Contenu signalé.")
        res = self.client.post(f"/api/owner/properties/{prop.id}/reactivate/")
        self.assertEqual(res.status_code, 400)


class PublicListingTests(APITestCase):
    def setUp(self):
        owner = make_owner()
        owner.phone = "+22890000000"
        owner.save()
        self.pub = make_property(owner, status=Property.Status.PUBLISHED, rooms_count=3)
        make_property(owner, title="Studio Tokoin", neighborhood="Tokoin", rent=30000,
                      property_type="studio", status=Property.Status.PUBLISHED)
        self.draft = make_property(owner, title="Brouillon", status=Property.Status.DRAFT)

    def titles(self, query=""):
        return [p["title"] for p in self.client.get(f"/api/properties/{query}").data["results"]]

    def test_only_published_listed(self):
        self.assertNotIn("Brouillon", self.titles())
        self.assertEqual(self.client.get(f"/api/properties/{self.draft.id}/").status_code, 404)

    def test_filters(self):
        self.assertEqual(self.titles("?max_rent=40000"), ["Studio Tokoin"])
        self.assertEqual(self.titles("?neighborhood=tok"), ["Studio Tokoin"])
        self.assertEqual(self.titles("?min_rooms=2"), ["Appartement à Bè"])
        self.assertEqual(len(self.titles("?city=lomé")), 2)

    def test_phone_hidden_from_anonymous(self):
        res = self.client.get(f"/api/properties/{self.pub.id}/")
        self.assertIsNone(res.data["owner"]["phone"])
        tenant = User.objects.create_user(email="t@example.com", password=PASSWORD)
        self.client.force_authenticate(tenant)
        res = self.client.get(f"/api/properties/{self.pub.id}/")
        self.assertEqual(res.data["owner"]["phone"], "+22890000000")
        self.assertEqual(tenant.view_history.count(), 1)


class AdminDecisionTests(TestCase):
    def test_approve_and_reject_notify_owner(self):
        owner = make_owner()
        prop = make_property(owner, status=Property.Status.PENDING)
        services.approve_property(prop)
        self.assertEqual(prop.status, "published")
        self.assertEqual(len(mail.outbox), 1)

        other = make_property(owner, status=Property.Status.PENDING)
        services.reject_property(other, "Photos floues.")
        self.assertEqual(other.status, "rejected")
        self.assertIn("Photos floues.", mail.outbox[1].body)
        self.assertEqual(Notification.objects.filter(user=owner).count(), 2)

    def test_cannot_approve_draft(self):
        prop = make_property(make_owner())
        with self.assertRaises(services.BusinessError):
            services.approve_property(prop)
