# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

import operator

from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render
from django.core.paginator import Paginator, Page, EmptyPage, PageNotAnInteger
from django import forms

from crispy_forms import helper

from elasticsearch_dsl.query import Q

from .models import Author, Book
from .documents import BookDocument
from .helpers import DateInput, SearchResults


class SearchForm(forms.Form):
    query = forms.CharField(
        label=_("Full-text Search Query"),
        required=False,
    )
    title = forms.CharField(
        label=_("Title"),
        required=False,
    )
    authors = forms.ModelMultipleChoiceField(
        label=_("Authors"),
        queryset=Author.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )
    published_from = forms.DateField(
        label=_("Published from"),
        required=False,
        widget=DateInput(),
    )
    published_till = forms.DateField(
        label=_("Published till"),
        required=False,
        widget=DateInput(),
    )


def book_list(request):
    paginate_by = 20

    search = BookDocument.search()

    form = SearchForm(data=request.GET)
    form.helper = helper.FormHelper()
    form.helper.form_tag = False
    form.helper.disable_csrf = True

    if form.is_valid():

        query = form.cleaned_data['query']
        if query:
            search = search.query("multi_match", query=query, fields=["title", "authors.author_name", "authors.last_name", "authors.first_name"], fuzziness=3)

        title = form.cleaned_data['title']
        if title:
            search = search.query("fuzzy", title=title)

        authors = form.cleaned_data['authors']
        if authors:
            author_queries = []
            for author in authors:
                author_queries.append(
                    Q('nested', path="authors", query=Q("match", authors__pk=author.pk))
                )
            search = search.query(reduce(operator.ior, author_queries))

        published_from = form.cleaned_data['published_from']
        if published_from:
            search = search.filter("range", publishing_date={"gte": published_from})

        published_till = form.cleaned_data['published_till']
        if published_till:
            search = search.filter("range", publishing_date={"lte": published_till})

    search = search.highlight('title')

    search_results = SearchResults(search)

    paginator = Paginator(search_results, paginate_by)
    page_number = request.GET.get("page")
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        # If page parameter is not an integer, show first page.
        page = paginator.page(1)
    except EmptyPage:
        # If page parameter is out of range, show last existing page.
        page = paginator.page(paginator.num_pages)

    context = {
        'object_list': page,
        'form': form,
    }
    return render(request, "library/book_list.html", context)
