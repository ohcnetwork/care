from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.contrib.auth.views import redirect_to_login

from .forms import FacilityCreationForm, FacilityCapacityCreationForm
from .models import Facility, FacilityCapacity


class StaffRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type == 10:
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect_to_login(self.request.get_full_path())


class FacilityCreation(LoginRequiredMixin, StaffRequiredMixin, View):

    form_class = FacilityCreationForm
    template = "facility/facility_creation.html"

    def get(self, request):
        try:
            form = self.form_class()
            return render(request, self.template, {"form": form})
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")

    def post(self, request):
        try:
            data = request.POST
            form = self.form_class(data)
            if form.is_valid():
                facility_obj = form.save(commit=False)
                facility_obj.created_by = request.user
                facility_obj.save()
                return HttpResponseRedirect(
                    "/facility/{}/capacity/add".format(facility_obj.id)
                )
            return render(request, self.template, {"form": form})
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")


class FacilityCapacityCreation(LoginRequiredMixin, StaffRequiredMixin, View):
    form_class = FacilityCapacityCreationForm
    template = "facility/facility_capacity_creation.html"

    def get(self, request, pk):
        try:
            form = self.form_class()
            return render(request, self.template, {"form": form})
        except Exception as e:
            return HttpResponseRedirect("")

    def post(self, request, pk):
        try:
            data = request.POST
            form = self.form_class(data)
            if form.is_valid():
                duplicate = False
                facility_capacity_obj = form.save(commit=False)
                facility_obj = Facility.objects.get(id=pk)
                facility_capacity_obj.facility = facility_obj
                try:
                    facility_capacity_obj.save()
                    if "addmore" in data:
                        return redirect(
                            "facility:facility-capacity-create", facility_obj.id
                        )
                    else:
                        return redirect("facility:facility-view", facility_obj.id)
                except IntegrityError:
                    duplicate = True
            return render(
                request, self.template, {"form": form, "duplicate": duplicate}
            )
        except Exception as e:
            return HttpResponseRedirect("")


class FacilitiesView(LoginRequiredMixin, StaffRequiredMixin, View):

    template = "facility/facilities_view.html"

    def get(self, request):
        try:
            current_user = request.user
            data = Facility.objects.filter(created_by=current_user)
            return render(request, self.template, {"data": data})
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")


class FacilityView(LoginRequiredMixin, StaffRequiredMixin, View):

    template = "facility/facility_view.html"

    def get(self, request, pk):
        try:
            current_user = request.user
            facility_obj = Facility.objects.get(id=pk, created_by=current_user)
            data = FacilityCapacity.objects.filter(facility=facility_obj)
            return render(
                request, self.template, {"data": data, "facility": facility_obj}
            )
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")


class FacilityCapacityUpdation(LoginRequiredMixin, StaffRequiredMixin, View):
    form_class = FacilityCapacityCreationForm
    template = "facility/facility_capacity_updation.html"

    def get(self, request, fpk, cpk):
        try:
            current_user = request.user
            facility_obj = Facility.objects.get(id=fpk, created_by=current_user)
            capacity_obj = FacilityCapacity.objects.get(id=cpk, facility=facility_obj)
            form = self.form_class(instance=capacity_obj)
            return render(request, self.template, {"form": form})
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")

    def post(self, request, fpk, cpk):
        try:
            data = request.POST
            current_user = request.user
            facility_obj = Facility.objects.get(id=fpk, created_by=current_user)
            capacity_obj = FacilityCapacity.objects.get(id=cpk, facility=facility_obj)
            form = self.form_class(data, instance=capacity_obj)
            duplicate = False
            if form.is_valid():
                try:
                    form.save()
                    return redirect("facility:facility-view", facility_obj.id)
                except IntegrityError:
                    duplicate = True
            print(form)
            return render(
                request, self.template, {"form": form, "duplicate": duplicate}
            )
        except Exception as e:
            print(e)
            return HttpResponseRedirect("")

