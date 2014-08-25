# -*- coding: utf-8 -*-

# This file is part of IRIS: Infrastructure and Release Information System
#
# Copyright (C) 2013 Intel Corporation
#
# IRIS is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 2.0 as published by the Free Software Foundation.

"""
This is the base view file for the iris-submissions application.

Commonplace views such as index page is contained here.
"""

# pylint: disable=E1101,W0621

from django.shortcuts import render
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.decorators import api_view
from iris.core.models import Submission, SubmissionGroup, Product
from iris.submissions.serializers import SubmissionGroupSerializer


@login_required
def index(request):
    """
    This view returns the index page for the submissions application.
    """

    return render(request, 'submissions/index.html')

@login_required
def summary(request):
    """
    Submissions summary page view.

    Requesting the page with ?filter=submissions or ?filter=submissiongroups
    restricts the results accordingly to either Submissions or Groups.
    """
    kw = request.GET.get('kw', 'my')
    if kw == 'my':
        res = Submission.objects.filter(
            owner=request.user).order_by('created')

        from iris.core.injectors import inject_user_getters
        u2 = inject_user_getters(request.user)
        domains = [i.domain for i in u2.get_domainroles()]
        subdomains = [i.subdomain for i in u2.get_subdomainroles()]
        trees = [i.gittree for i in u2.get_gittreeroles()]

        title = 'My submissions'
    elif kw == 'all':
        # FIXME: sort by updated not created
        res = Submission.objects.all().order_by('created')
        title = 'All submissions'
    else:
        kw = request.GET.get('kw')
        res = Submission.objects.filter(
            Q(name__contains=kw) |
            Q(commit__startswith=kw) |
            Q(owner__email__startswith=kw) |
            Q(status=kw) |
            Q(gittree__gitpath__contains=kw)
            )
        title = 'Search for "%s"' % kw

    return render(request, 'submissions/summary.html', {
        'title': title,
        'results': res,
        })


@login_required
@permission_required('core.add_submissiongroup', raise_exception=True)
def create_group(request):
    """
    Submissions grouping view. REs create submission groups with this view.
    """

    submissions = Submission.objects.all()

    # First, filter result set by product condition, if any
    selected_product = request.GET.get('product', '')
    unselected_products = Product.objects.all()

    if selected_product:
        product_object = Product.objects.get(name__iexact=selected_product)
        unselected_products = Product.objects.exclude(id=product_object.id)
        submissions = submissions.filter(product=product_object)

    else:
        product_object = Product.objects.get(short__iexact='tizen')
        unselected_products = Product.objects.exclude(id=product_object.id)

    submissions = submissions.exclude(status__in=['ACCEPTED', 'REJECTED'])

    return render(request, 'submissions/create_group.html', {
        'submissions': submissions,
        'selected_product': product_object,
        'unselected_products': unselected_products })

# @login_required
@permission_required('core.add_submissiongroup', raise_exception=True)
@api_view(['GET', 'POST'])
def create_group_ajax(request):
    """
    Submissions creation view; for REs to create submissions.
    """

    # Parse submission IDs from the query dict, convert to integers for ORM
    submission_ids = request.POST.get('submissions', '').split(',')
    submission_ids = [int(s) for s in submission_ids if s]
    submissions = Submission.objects.filter(id__in=submission_ids)

    if not submissions:
        return Response({'error': 'Select submissions to group'}, 400)

    product_short = 'tizen'
    product = Product.objects.get(short__iexact=product_short)
    name = 'submit/%s/%s' % (product.short, now().strftime('%Y%m%d.%H%M%S'))
    author = request.user

    submissiongroup = SubmissionGroup.objects.create(name=name,
            author=author, product=product, status='NEW')

    for submission in submissions:
        submissiongroup.submissions.add(submission)

    return Response(SubmissionGroupSerializer(submissiongroup).data)
