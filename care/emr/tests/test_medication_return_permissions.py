from decimal import Decimal

from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from care.emr.models.location import FacilityLocation, FacilityLocationOrganization
from care.emr.models.supply_delivery import DeliveryOrder, SupplyDelivery
from care.emr.resources.inventory.supply_delivery.delivery_order import (
    SupplyDeliveryOrderStatusOptions,
)
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)
from care.emr.tests.test_supply_delivery import TestSupplyDeliveryViewSetBase
from care.security.permissions.supply_delivery import SupplyDeliveryPermissions


class MedicationReturnPermissionsAPITest(TestSupplyDeliveryViewSetBase):
    def setUp(self):
        super().setUp()
        self.return_order = self.create_delivery_order(
            name="Patient return",
            destination=self.destination,
            patient=self.patient,
            status=SupplyDeliveryOrderStatusOptions.draft.value,
        )
        self.return_delivery = self.create_supply_delivery(
            order=self.return_order,
            supplied_item=self.product,
            supplied_inventory_item=self.inventory_item_destination,
            supplied_item_quantity=Decimal(10),
            status=SupplyDeliveryStatusOptions.in_progress.value,
        )
        self.order_list_url = reverse(
            "delivery-order-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def authenticate_with_permissions(self, *permissions):
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[permission.name for permission in permissions]
        )
        self.attach_role_facility_organization_user(
            user=user,
            role=role,
            facility_organization=self.facility_organization,
        )
        self.client.force_authenticate(user=user)

    def order_detail_url(self, order):
        return reverse(
            "delivery-order-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": order.external_id,
            },
        )

    def order_data(self, *, patient=None):
        data = {
            "name": "New delivery order",
            "status": SupplyDeliveryOrderStatusOptions.draft.value,
            "destination": str(self.destination.external_id),
        }
        if patient:
            data["patient"] = str(patient.external_id)
        return data

    def delivery_data(self, order):
        return self.create_supply_delivery_data(
            order=str(order.external_id),
            supplied_item=str(self.product.external_id),
            quantity=Decimal(10),
        )

    def assert_result_ids(self, response, expected):
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            {item["id"] for item in response.data["results"]},
            {str(item.external_id) for item in expected},
        )

    def test_return_permissions_allow_order_create_retrieve_and_update(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_medication_return,
            SupplyDeliveryPermissions.can_write_medication_return,
        )
        response = self.client.post(
            self.order_list_url, self.order_data(patient=self.patient), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        order = DeliveryOrder.objects.get(external_id=response.data["id"])
        response = self.client.get(self.order_detail_url(order))
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.put(
            self.order_detail_url(order),
            {"name": "Updated return", "status": "pending"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        order.refresh_from_db()
        self.assertEqual(order.name, "Updated return")
        self.assertEqual(order.status, "pending")

    def test_return_permissions_allow_delivery_create_retrieve_and_update(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_medication_return,
            SupplyDeliveryPermissions.can_write_medication_return,
        )
        response = self.client.post(
            self.base_url, self.delivery_data(self.return_order), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        detail_url = self.get_detail_url(response.data["id"])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.put(detail_url, {"status": "completed"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "completed")

    def test_purchase_permissions_do_not_authorize_returns(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_supply_delivery,
            SupplyDeliveryPermissions.can_write_supply_delivery,
            SupplyDeliveryPermissions.can_write_external_supply_delivery,
        )
        responses = [
            self.client.post(
                self.order_list_url,
                self.order_data(patient=self.patient),
                format="json",
            ),
            self.client.get(self.order_detail_url(self.return_order)),
            self.client.put(
                self.order_detail_url(self.return_order),
                {"name": "Unauthorized return", "status": "pending"},
                format="json",
            ),
            self.client.post(
                self.base_url, self.delivery_data(self.return_order), format="json"
            ),
            self.client.get(self.get_detail_url(self.return_delivery.external_id)),
            self.client.put(
                self.get_detail_url(self.return_delivery.external_id),
                {"status": "completed"},
                format="json",
            ),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 403, response.data)
        self.return_order.refresh_from_db()
        self.return_delivery.refresh_from_db()
        self.assertEqual(self.return_order.status, "draft")
        self.assertEqual(self.return_delivery.status, "in_progress")

    def test_return_permissions_do_not_authorize_purchases(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_medication_return,
            SupplyDeliveryPermissions.can_write_medication_return,
        )
        purchase_order = self.delivery_order_destination_external
        responses = [
            self.client.post(self.order_list_url, self.order_data(), format="json"),
            self.client.get(self.order_detail_url(purchase_order)),
            self.client.put(
                self.order_detail_url(purchase_order),
                {"name": "Unauthorized purchase", "status": "pending"},
                format="json",
            ),
            self.client.post(
                self.base_url, self.delivery_data(purchase_order), format="json"
            ),
            self.client.get(
                self.get_detail_url(self.purchase_order_destination.external_id)
            ),
            self.client.put(
                self.get_detail_url(self.purchase_order_destination.external_id),
                {"status": "entered_in_error"},
                format="json",
            ),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 403, response.data)

    def test_return_read_permission_does_not_allow_writes(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_medication_return
        )
        response = self.client.get(self.order_detail_url(self.return_order))
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(
            self.get_detail_url(self.return_delivery.external_id)
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.put(
            self.order_detail_url(self.return_order),
            {"name": "Unauthorized update", "status": "pending"},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.put(
            self.get_detail_url(self.return_delivery.external_id),
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_return_write_permission_does_not_allow_reads(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_write_medication_return
        )
        response = self.client.put(
            self.order_detail_url(self.return_order),
            {"name": "Updated return", "status": "pending"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(self.order_detail_url(self.return_order))
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.get(
            self.get_detail_url(self.return_delivery.external_id)
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_order_list_defaults_to_purchases_even_for_superusers(self):
        self.client.force_authenticate(user=self.superuser)
        purchases = [
            self.delivery_order_destination_external,
            self.delivery_order_internal,
        ]
        for params, expected in [
            ({}, purchases),
            ({"patient_return": "false"}, purchases),
            ({"patient_return": "true"}, [self.return_order]),
        ]:
            with self.subTest(params=params):
                self.assert_result_ids(
                    self.client.get(
                        self.order_list_url,
                        {"destination": str(self.destination.external_id), **params},
                    ),
                    expected,
                )

    def test_order_lists_require_an_origin_or_destination(self):
        for user in (self.superuser, self.user):
            self.client.force_authenticate(user=user)
            for params in [
                {},
                {"patient_return": "true"},
                {"status": "draft"},
                {"patient": str(self.patient.external_id)},
                {"patient_isnull": "false"},
            ]:
                with self.subTest(user=user.external_id, params=params):
                    response = self.client.get(self.order_list_url, params)
                    self.assertEqual(response.status_code, 400, response.data)

    def test_return_order_lists_require_a_destination(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_medication_return
        )
        response = self.client.get(
            self.order_list_url,
            {"patient_return": "true", "origin": str(self.origin.external_id)},
        )
        self.assertEqual(response.status_code, 400, response.data)

    def test_return_order_lists_authorize_only_the_destination(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_medication_return
        )
        unrelated_origin = baker.make(FacilityLocation, facility=self.facility)
        self.assert_result_ids(
            self.client.get(
                self.order_list_url,
                {
                    "patient_return": "true",
                    "destination": str(self.destination.external_id),
                    "origin": str(unrelated_origin.external_id),
                },
            ),
            [],
        )

    def test_order_list_flag_selects_the_category_and_permission(self):
        purchases = [
            self.delivery_order_destination_external,
            self.delivery_order_internal,
        ]
        cases = [
            ([SupplyDeliveryPermissions.can_read_supply_delivery], True, False),
            (
                [SupplyDeliveryPermissions.can_read_medication_return],
                False,
                True,
            ),
            (
                [
                    SupplyDeliveryPermissions.can_read_supply_delivery,
                    SupplyDeliveryPermissions.can_read_medication_return,
                ],
                True,
                True,
            ),
            ([], False, False),
        ]
        for permissions, can_read_purchases, can_read_returns in cases:
            with self.subTest(permissions=permissions):
                self.authenticate_with_permissions(*permissions)
                for params, expected, allowed in [
                    ({}, purchases, can_read_purchases),
                    ({"patient_return": "false"}, purchases, can_read_purchases),
                    (
                        {"patient_return": "true"},
                        [self.return_order],
                        can_read_returns,
                    ),
                    (
                        {"patient": str(self.patient.external_id)},
                        [],
                        can_read_purchases,
                    ),
                    ({"patient_isnull": "false"}, [], can_read_purchases),
                    (
                        {
                            "patient_return": "true",
                            "patient": str(self.patient.external_id),
                        },
                        [self.return_order],
                        can_read_returns,
                    ),
                ]:
                    response = self.client.get(
                        self.order_list_url,
                        {"destination": str(self.destination.external_id), **params},
                    )
                    if allowed:
                        self.assert_result_ids(response, expected)
                    else:
                        self.assertEqual(response.status_code, 403, response.data)

    def test_location_order_list_permission_matches_the_selected_category(self):
        for permission, patient_return, orders in [
            (
                SupplyDeliveryPermissions.can_read_supply_delivery,
                "false",
                [
                    self.delivery_order_destination_external,
                    self.delivery_order_internal,
                ],
            ),
            (
                SupplyDeliveryPermissions.can_read_medication_return,
                "true",
                [self.return_order],
            ),
        ]:
            with self.subTest(permission=permission):
                self.authenticate_with_permissions(permission)
                params = {
                    "destination": str(self.destination.external_id),
                    "patient_return": patient_return,
                }
                self.assert_result_ids(
                    self.client.get(self.order_list_url, params), orders
                )
                params["patient_return"] = (
                    "true" if patient_return == "false" else "false"
                )
                response = self.client.get(self.order_list_url, params)
                self.assertEqual(response.status_code, 403, response.data)

    def test_delivery_list_permission_comes_from_the_actual_parent_order(self):
        cases = [
            (
                SupplyDeliveryPermissions.can_read_supply_delivery,
                self.delivery_order_destination_external,
                self.purchase_order_destination,
                200,
            ),
            (
                SupplyDeliveryPermissions.can_read_supply_delivery,
                self.return_order,
                self.return_delivery,
                403,
            ),
            (
                SupplyDeliveryPermissions.can_read_medication_return,
                self.return_order,
                self.return_delivery,
                200,
            ),
            (
                SupplyDeliveryPermissions.can_read_medication_return,
                self.delivery_order_destination_external,
                self.purchase_order_destination,
                403,
            ),
        ]
        for permission, order, delivery, status_code in cases:
            with self.subTest(permission=permission, order=order.external_id):
                self.authenticate_with_permissions(permission)
                for flag in (None, "false", "true"):
                    params = {"order": str(order.external_id)}
                    if flag is not None:
                        params["patient_return"] = flag
                    response = self.client.get(self.base_url, params)
                    if status_code == status.HTTP_200_OK:
                        self.assert_result_ids(response, [delivery])
                    else:
                        self.assertEqual(
                            response.status_code, status_code, response.data
                        )

    def test_list_permissions_are_evaluated_per_category_and_organization(self):
        other_organization = self.create_facility_organization(facility=self.facility)
        other_location = baker.make(FacilityLocation, facility=self.facility)
        baker.make(
            FacilityLocationOrganization,
            location=other_location,
            organization=other_organization,
        )
        other_purchase = self.create_delivery_order(destination=other_location)
        other_return = self.create_delivery_order(
            destination=other_location, patient=self.patient
        )
        other_return_delivery = baker.make(
            SupplyDelivery,
            order=other_return,
            supplied_item=self.product,
            supplied_item_quantity=10,
            status="in_progress",
        )
        baker.make(
            SupplyDelivery,
            order=other_purchase,
            supplied_item=self.product,
            supplied_item_quantity=10,
            status="in_progress",
        )
        user = self.create_user()
        for organization, permission in [
            (
                self.facility_organization,
                SupplyDeliveryPermissions.can_read_supply_delivery,
            ),
            (other_organization, SupplyDeliveryPermissions.can_read_medication_return),
        ]:
            role = self.create_role_with_permissions(permissions=[permission.name])
            self.attach_role_facility_organization_user(
                user=user, role=role, facility_organization=organization
            )
        self.client.force_authenticate(user=user)

        for location, patient_return, expected_orders in [
            (
                self.destination,
                "false",
                [
                    self.delivery_order_destination_external,
                    self.delivery_order_internal,
                ],
            ),
            (other_location, "true", [other_return]),
        ]:
            with self.subTest(location=location.external_id):
                params = {
                    "destination": str(location.external_id),
                    "patient_return": patient_return,
                }
                self.assert_result_ids(
                    self.client.get(self.order_list_url, params), expected_orders
                )
                params["patient_return"] = (
                    "true" if patient_return == "false" else "false"
                )
                response = self.client.get(self.order_list_url, params)
                self.assertEqual(response.status_code, 403, response.data)
        self.assert_result_ids(
            self.client.get(self.base_url, {"order": str(other_return.external_id)}),
            [other_return_delivery],
        )

    def test_order_lists_are_scoped_to_the_requested_facility(self):
        other_facility = self.create_facility(user=self.superuser)
        other_organization = self.create_facility_organization(facility=other_facility)
        other_location = baker.make(FacilityLocation, facility=other_facility)
        baker.make(
            FacilityLocationOrganization,
            location=other_location,
            organization=other_organization,
        )
        other_return = self.create_delivery_order(
            destination=other_location, patient=self.patient
        )
        user = self.create_user()
        role = self.create_role_with_permissions(
            permissions=[SupplyDeliveryPermissions.can_read_medication_return.name]
        )
        for organization in [self.facility_organization, other_organization]:
            self.attach_role_facility_organization_user(
                user=user, role=role, facility_organization=organization
            )
        self.client.force_authenticate(user=user)

        self.assert_result_ids(
            self.client.get(
                self.order_list_url,
                {
                    "patient_return": "true",
                    "destination": str(self.destination.external_id),
                },
            ),
            [self.return_order],
        )
        other_order_list_url = reverse(
            "delivery-order-list",
            kwargs={"facility_external_id": other_facility.external_id},
        )
        self.assert_result_ids(
            self.client.get(
                other_order_list_url,
                {
                    "patient_return": "true",
                    "destination": str(other_location.external_id),
                },
            ),
            [other_return],
        )
        self.assert_result_ids(
            self.client.get(
                self.order_list_url,
                {
                    "patient_return": "true",
                    "destination": str(other_location.external_id),
                },
            ),
            [],
        )

    def test_return_permissions_are_scoped_to_the_destination_organizations(self):
        inaccessible_location = baker.make(FacilityLocation, facility=self.facility)
        inaccessible_order = self.create_delivery_order(
            name="Other department return",
            destination=inaccessible_location,
            patient=self.patient,
            status="draft",
        )
        inaccessible_delivery = baker.make(
            SupplyDelivery,
            order=inaccessible_order,
            supplied_item=self.product,
            supplied_item_quantity=10,
            status="in_progress",
        )
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_read_medication_return,
            SupplyDeliveryPermissions.can_write_medication_return,
        )
        response = self.client.get(self.order_detail_url(inaccessible_order))
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.get(
            self.get_detail_url(inaccessible_delivery.external_id)
        )
        self.assertEqual(response.status_code, 403, response.data)
        data = self.order_data(patient=self.patient)
        data["destination"] = str(inaccessible_location.external_id)
        response = self.client.post(self.order_list_url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assert_result_ids(
            self.client.get(
                self.order_list_url,
                {
                    "patient_return": "true",
                    "destination": str(self.destination.external_id),
                },
            ),
            [self.return_order],
        )
        response = self.client.get(
            self.order_list_url,
            {
                "patient_return": "true",
                "destination": str(inaccessible_location.external_id),
            },
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_upsert_cannot_bypass_return_permissions(self):
        self.authenticate_with_permissions(
            SupplyDeliveryPermissions.can_write_supply_delivery,
            SupplyDeliveryPermissions.can_write_external_supply_delivery,
        )
        order_count = DeliveryOrder.objects.count()
        delivery_count = SupplyDelivery.objects.count()
        order_upsert_url = reverse(
            "delivery-order-upsert",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        response = self.client.post(
            order_upsert_url,
            {"datapoints": [self.order_data(patient=self.patient)]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        response = self.client.post(
            reverse("supply_delivery-upsert"),
            {"datapoints": [self.delivery_data(self.return_order)]},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(DeliveryOrder.objects.count(), order_count)
        self.assertEqual(SupplyDelivery.objects.count(), delivery_count)
