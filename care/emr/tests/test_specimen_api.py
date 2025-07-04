from django.urls import reverse
from care.utils.tests.base import CareAPITestBase
from model_bakery import baker
from care.security.permissions.specimen import SpecimenPermissions
from care.security.permissions.encounter import EncounterPermissions
from care.emr.resources.specimen.spec import SpecimenStatusOptions
from care.security.permissions.service_request import ServiceRequestPermissions
from care.security.permissions.facility_organization import FacilityOrganizationPermissions
from care.emr.models.specimen import Specimen
from care.emr.models.location import FacilityLocation
class TestSpecimenViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        # Create basic users
        self.user = self.create_user()
        self.superuser = self.create_super_user()

        # Create patient and facility
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.facility_location = self.create_facility_location()
        # Create encounter and service request
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            current_location=self.facility_location
        )

        self.service_request = self.create_service_request(
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            locations=[self.facility_location.id]
        )

        self.role = self.create_role_with_permissions(
            role_name="Admin",
            permissions=[
                SpecimenPermissions.can_read_specimen.value,
                SpecimenPermissions.can_write_specimen.value,
                EncounterPermissions.can_read_encounter.value,
                ServiceRequestPermissions.can_read_service_request.value,
                FacilityOrganizationPermissions.can_view_facility_organization.value,

            ]
        )


    def get_detail_url(self, facility_external_id, external_id):
        return reverse("specimen-detail", kwargs={
            "facility_external_id": facility_external_id,
            "external_id": external_id
        })


    def create_specimen(self, **kwargs):
        specimen = baker.make(
            "emr.Specimen",
            facility=self.facility,
            patient=self.patient,
            encounter=self.encounter,
            service_request=self.service_request,
            status=SpecimenStatusOptions.available.value,
            **kwargs
        )
        return specimen

    def create_facility_location(self):
        from care.emr.models.location import FacilityLocation

        location = baker.make(
            FacilityLocation,
            name=f"Test facility Locations",
            facility=self.facility,
            status="active",
        )
        return location


    def test_retrieve_with_read_permission(self):
        """Test that a user with read_specimen permission can retrieve a specimen"""
        # Create the specimen first
        specimen = self.create_specimen(
            created_by=self.user,
        )

        # Step 1: Debug role permissions - CRITICAL FIX HERE
        from care.security.models import RolePermission

        print("\n=== DEBUG AUTHORIZATION ===")
        print(f"1. Role ID and Permissions:")
        role_perms = RolePermission.objects.filter(role=self.role)
        permission_slugs = [rp.permission.slug for rp in role_perms]
        print(f"   Role ID: {self.role.id}")
        print(f"   Role name: {self.role.name}")
        print(f"   Permission slugs: {permission_slugs}")

        # Important check - what format is the specimen permission actually stored in?
        print(f"   Specimen permission value: {SpecimenPermissions.can_read_specimen.value}")
        print(f"   Specimen permission name: {SpecimenPermissions.can_read_specimen.name}")
        print(f"   Is value in permissions: {SpecimenPermissions.can_read_specimen.value in permission_slugs}")
        print(f"   Is name in permissions: {SpecimenPermissions.can_read_specimen.name in permission_slugs}")

        # Step 2: Fix location cache
        print("\n2. Location cache:")
        print(f"   Before: {self.facility_location.facility_organization_cache}")
        self.facility_location.facility_organization_cache = [self.facility_organization.id]
        self.facility_location.save()
        print(f"   After: {self.facility_location.facility_organization_cache}")

        # Step 3: Fix service request locations
        print("\n3. Service request locations:")
        print(f"   Before: {self.service_request.locations}")
        self.service_request.locations = [self.facility_location.id]
        self.service_request.save()
        print(f"   After: {self.service_request.locations}")

        # Step 4: Assign role to user
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )

        from care.security.authorization import AuthorizationController

        print("\n4. Service request authorization:")
        print(f"   Available AuthorizationController methods: {[m for m in dir(AuthorizationController) if not m.startswith('_')]}")

        # Try direct import
        try:
            from care.security.authorization.service_request import ServiceRequestAccess
            sr_auth = ServiceRequestAccess()
            print("   Created ServiceRequestAccess instance directly")

            specimen_perm = SpecimenPermissions.can_read_specimen.name

            can_read = sr_auth.has_permission_on_service_request(
                self.user,
                self.service_request,
                specimen_perm
            )
            print(f"   Permission check with '{specimen_perm}': {can_read}")

            # Also try the direct method
            direct_check = sr_auth.can_read_specimen(self.user, self.service_request)
            print(f"   Direct can_read_specimen check: {direct_check}")
        except Exception as e:
            print(f"   ERROR accessing ServiceRequestAccess: {e}")

        # Step 6: Test API access
        self.client.force_authenticate(user=self.user)
        url = self.get_detail_url(self.facility.external_id, specimen.external_id)
        response = self.client.get(url)

        print(f"\n5. API Response: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error data: {response.data}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(specimen.external_id))
        print("=== END DEBUG ===")
