from django.conf import settings
from django.core.management.base import BaseCommand

from care.emr.resources.encounter.constants import StatusChoices
from care.emr.resources.location.spec import (
    FacilityLocationFormChoices,
    FacilityLocationModeChoices,
)
from care.emr.resources.organization.spec import OrganizationTypeChoices
from care.fixtures.constants import (
    INVENTORY_ITEMS,
    LAB_TESTS,
    MANAGING_ORG_USERS,
    HealthcareServiceInternalType,
)
from care.fixtures.context import care_fixture_context


class Command(BaseCommand):
    help = "Load fixture data for local development and testing"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write(
                self.style.ERROR(
                    "This command should not be run in production. Exiting..."
                )
            )
            return

        self.stdout.write(self.style.WARNING("\nStarting fixtures...\n"))

        with care_fixture_context() as base:
            self.load_fixtures(base)

        self.stdout.write(self.style.SUCCESS("\nAll fixtures loaded successfully!\n"))

    def load_fixtures(self, base):  # noqa: PLR0915
        log = self.stdout.write

        log("\n▶ Organizations")
        geo_organization = base.create_organization(
            org_type=OrganizationTypeChoices.govt.value, name="Kerala"
        )
        log(f"  Geo: {geo_organization['name']} ({geo_organization['id']})")

        district = base.create_organization(
            org_type=OrganizationTypeChoices.govt.value,
            parent=geo_organization["id"],
            name="Ernakulam",
        )
        log(f"  District: {district['name']} ({district['id']})")

        suppliers = []
        for _ in range(3):
            supplier = base.create_organization(
                org_type=OrganizationTypeChoices.product_supplier.value,
                name=f"Supplier {base.fake.company()}",
            )
            suppliers.append(supplier)
            log(f"  Supplier: {supplier['name']} ({supplier['id']})")

        role_org_names = [
            "Volunteer",
            "Doctor",
            "Staff",
            "Nurse",
            "Administrator",
            "Facility Admin",
        ]
        role_orgs = {}
        for name in role_org_names:
            role_orgs[name] = base.create_organization(
                org_type=OrganizationTypeChoices.role.value, name=name
            )
            log(f"  Role Org: {name} ({role_orgs[name]['id']})")

        log("\n▶ Facility")
        facility = base.create_facility(
            geo_organization["id"],
            name="FACILITY WITH PATIENTS",
            facility_type="Private Hospital",
        )
        facility_id = facility["id"]
        log(f"  {facility['name']} ({facility_id})")

        log("\n▶ Departments")
        existing = base.get_facility_organizations(facility_id)
        departments = {}
        admin_org = next((o for o in existing if o["name"] == "Administration"), None)
        if admin_org:
            departments["Administration"] = admin_org
            log(f"  Administration ({admin_org['id']}) (auto-created)")

        for name in ["General Medicine", "Emergency", "Laboratory", "Pharmacy"]:
            dept = base.create_facility_organization(facility_id, name=name)
            departments[name] = dept
            log(f"  {name} ({dept['id']})")

        general_medicine = departments["General Medicine"]

        log("\n▶ Locations")
        ward = base.create_location(
            facility_id,
            name="Ward A",
            form=FacilityLocationFormChoices.wa.value,
            mode=FacilityLocationModeChoices.kind.value,
            organizations=[general_medicine["id"]],
        )
        log(f"  Ward: {ward['name']} ({ward['id']})")

        for idx in range(1, 6):
            bed = base.create_location(
                facility_id,
                name=f"Bed {idx}",
                description=f"Bed {idx} in {ward['name']}",
                parent=ward["id"],
                form=FacilityLocationFormChoices.bd.value,
                mode=FacilityLocationModeChoices.instance.value,
                organizations=[general_medicine["id"]],
            )
            log(f"  Bed: {bed['name']} ({bed['id']})")

        log("\n▶ Devices")
        for i in range(1, 6):
            device = base.create_device(facility_id, registered_name=f"Device {i}")
            log(f"  {device.get('registered_name')} ({device['id']})")

        log("\n▶ Users")
        password = "Ohcn@123"
        roles = base.get_roles()
        default_users = [
            ("Doctor", "care-doctor"),
            ("Staff", "care-staff"),
            ("Nurse", "care-nurse"),
            ("Administrator", "care-admin"),
            ("Volunteer", "care-volunteer"),
            ("Facility Admin", "care-fac-admin"),
        ]
        for role_name, username in default_users:
            if role_name not in roles or role_name not in role_orgs:
                log(f"   {role_name} not found, skipping")
                continue
            base.create_user(
                geo_organization["id"],
                role_orgs=[
                    {
                        "organization": role_orgs[role_name]["id"],
                        "role": roles[role_name]["id"],
                    }
                ],
                username=username,
                email=f"{username}@care.test",
                password=password,
            )
            log(f"  {username} / {password} (role: {role_name})")

        log("\n▶ Patients")
        patients = []
        for _ in range(10):
            patient = base.create_patient(geo_organization["id"])
            patients.append(patient)
            log(f"  {patient['name']} ({patient['id']})")

        log("\n▶ Encounters")
        for patient in patients:
            encounter = base.create_encounter(
                patient["id"],
                facility_id,
                organizations=[general_medicine["id"]],
                status=StatusChoices.in_progress.value,
            )
            log(f"  {patient['name']} → {encounter['status']} ({encounter['id']})")

        log("\n▶ Questionnaires")
        results = base.load_questionnaires_from_file([geo_organization["id"]])
        for questionnaire in results:
            log(f"  {questionnaire.get('title', 'Unknown')} ({questionnaire['id']})")
        if not results:
            log("  No questionnaires loaded")

        self.load_lab_definitions(base, facility_id, departments, log)

        self.load_inventory(base, facility_id, departments, suppliers[0]["id"], log)

        self.setup_managing_organization(
            base, role_orgs, geo_organization["id"], password, log
        )

        log("\n" + "=" * 50)
        log("  Superuser:  admin / admin")
        log("=" * 50 + "\n")

    def load_lab_definitions(self, base, facility_id, departments, log):
        log("\n▶ Lab Definitions")
        general_medicine = departments["General Medicine"]

        lab_location = base.create_location(
            facility_id,
            name="Bio-Chemistry Lab",
            form=FacilityLocationFormChoices.ro.value,
            mode=FacilityLocationModeChoices.kind.value,
            organizations=[general_medicine["id"]],
        )
        log(f"  Location: {lab_location['name']} ({lab_location['id']})")

        lab_charge_category = base.create_resource_category(
            facility_id, "Lab Tests", "charge_item_definition"
        )
        lab_activity_category = base.create_resource_category(
            facility_id, "Lab Tests", "activity_definition"
        )
        log(f"  Category: Lab Tests (charge: {lab_charge_category['id']})")
        log(f"  Category: Lab Tests (activity: {lab_activity_category['id']})")

        lab_service = base.create_healthcare_service(
            facility_id,
            name="Pathology Lab",
            internal_type=HealthcareServiceInternalType.lab.value,
            styling_metadata={"careIcon": "microscope"},
            locations=[lab_location["id"]],
        )
        log(f"  Service: {lab_service['name']}")

        for test in LAB_TESTS:
            base.create_lab_test(
                facility_id,
                test,
                service_id=lab_service["id"],
                location_id=lab_location["id"],
                charge_category_slug=lab_charge_category["slug"],
                activity_category_slug=lab_activity_category["slug"],
            )
            log(f"  Test: {test['activity']['title']}")

    def load_inventory(self, base, facility_id, departments, supplier_id, log):
        log("\n▶ Inventory")
        general_medicine = departments["General Medicine"]

        pharmacy_location = base.create_location(
            facility_id,
            name="Pharmacy",
            form=FacilityLocationFormChoices.ro.value,
            mode=FacilityLocationModeChoices.kind.value,
            organizations=[general_medicine["id"]],
        )
        log(f"  Location: {pharmacy_location['name']} ({pharmacy_location['id']})")

        pharmacy_service = base.create_healthcare_service(
            facility_id,
            name="Main Pharmacy",
            internal_type=HealthcareServiceInternalType.pharmacy.value,
            styling_metadata={},
            locations=[pharmacy_location["id"]],
        )
        log(f"  Service: {pharmacy_service['name']}")

        # Build category map
        category_names = {item["category"] for item in INVENTORY_ITEMS}
        categories = {}
        for category_name in category_names:
            categories[category_name] = {
                "product_knowledge": base.create_resource_category(
                    facility_id, category_name, "product_knowledge"
                )["slug"],
                "charge_item_definition": base.create_resource_category(
                    facility_id, category_name, "charge_item_definition"
                )["slug"],
            }
        log(f"  Categories: {', '.join(category_names)}")

        products = []
        for item in INVENTORY_ITEMS:
            product = base.create_inventory_item(
                facility_id,
                item,
                categories[item["category"]],
            )
            log(f"  Product: {item['product_knowledge']['name']}")
            products.append((product, item["stock_quantity"]))

        order = base.create_delivery_order(
            facility_id,
            name="Initial Stock Delivery",
            destination=pharmacy_location["id"],
            supplier=supplier_id,
        )
        log(f"  Delivery Order: {order['name']} ({order['id']})")

        for product, quantity in products:
            base.create_supply_delivery(
                order=order["id"],
                supplied_item_quantity=quantity,
                supplied_item=product["id"],
            )
        log(f"  Supply Deliveries: {len(products)} items delivered")

    def setup_managing_organization(self, base, role_orgs, geo_id, password, log):
        """Create a managing organization, link it to all role orgs, and assign users."""
        log("\n▶ Managing Organization")

        role_org_roles = base.get_role_org_roles()

        managing_org = base.create_organization(
            org_type=OrganizationTypeChoices.role.value, name="Health Department"
        )
        managing_org_id = managing_org["id"]
        log(f"  Created: {managing_org['name']} ({managing_org_id})")

        for _name, org in role_orgs.items():
            base.link_managing_org(org["id"], managing_org_id)
        log(f"  Linked to {len(role_orgs)} role orgs")

        for user_def in MANAGING_ORG_USERS:
            role_id = role_org_roles[user_def["role"]]["id"]

            if user_def["action"] == "create":
                user = base.create_user(
                    geo_id,
                    username=user_def["username"],
                    email=f"{user_def['username']}@care.test",
                    password=password,
                )
                base.assign_org_role(managing_org_id, user["id"], role_id)
                log(f"  {user_def['role']:<10} {user_def['username']:<25} {password}")

            elif user_def["action"] == "assign":
                try:
                    user_data = base.get_user(user_def["username"])
                    base.assign_org_role(managing_org_id, user_data["id"], role_id)
                    log(f"  Assigned {user_def['role']} to {user_def['username']}")
                except Exception as e:
                    log(
                        f"  Warning: Could not assign {user_def['role']} to {user_def['username']}: {e}"
                    )
