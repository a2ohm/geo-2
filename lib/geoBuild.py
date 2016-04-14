#! /usr/bin/python
# -*- coding-utf-8 -*-

import mmap
import yaml
import re
import os

import jinja2

class geoBuild():

    skill_badges = {
            "solder" : ("Souder", "./i/badges/solder.png")
            }

    # Regex
    regex = {   'title': "^(#+) (.+)$",
                'meta': "^\$(\w+)(: (.+))?$"
                }

    # Templates
    template = {    'intro': 'intro.html'}

    def __init__(self, doc_in, root_out = "./doc"):
        """Init the parser.
        """

        # Save arguments
        self.doc_in = doc_in

        # Set the header
        self.header = None
        self.header_limit = -1
        # Set the img references dict
        self.imgRef = {}

        # Set the input file
        self.f_in = None

        # Set the output directory
        self.root_out = root_out
        self.dir_out = root_out
        
        self.items = {}
        self.pagination = {}

        # Environment
        self.env = jinja2.Environment(
                loader=jinja2.FileSystemLoader('./templates'))

    def __enter__(self):
        """Open the file.
        """
        self.f_in = open(self.doc_in, 'r')
        return self

    def __exit__(self, type, value, traceback):
        """Close the file.
        """
        self.f_in.close()

    def parseHeaderAndImg(self):
        """Parse the header of the file and the img references file.
        """

        # Use mmap to only read the header of the raw doc file. This
        # header is separated from the rest by "---".
        if self.header_limit < 0:
            f_in_mmap = mmap.mmap(self.f_in.fileno(),
                    0, access=mmap.ACCESS_READ)
            self.header_limit = f_in_mmap.find(b'---')

            if self.header_limit != -1:
                self.header = yaml.load(
                        f_in_mmap[0:self.header_limit])
            else:
                raise("Cannot load the header")

        # Load the image references file
        with open("%s_img.yaml" % self.doc_in[:-3], 'r') as f:
            self.imgRef = yaml.load(f)

        # Add im to items
        for item in self.header['items']:
            item['img'] = self.imgRef['items'][item['id']]

        # Parse the items list for further uses
        for item in self.header["items"]:
            item_dict = {}
            item_dict["qty"] = item['qty']
            item_dict["description"] = item['description']
            item_dict["img"] = item['img']

            for item_id, item_name in zip(
                    item['id'].split(', '),
                    item['name'].split(', ')):
                item_dict["name"] = item_name
                item_dict['id'] = item_id
                self.items[item_id] = item_dict.copy()


    def parseSkills(self):
        """Parse skills.
        """

        skills = [
                (geoBuild.skill_badges[skill][0],
                 geoBuild.skill_badges[skill][1],
                 lvl)
                for skill, lvl in self.header.get("skills", [])]

        self.header['skills'] = skills


    def parse(self):
        """Parse the document.
        """
        # Parse the header and the img references file
        self.parseHeaderAndImg()

        # Parse skills
        self.parseSkills()

        # Do the pagination
        self.doPagination()


        # Set the output dir
        self.dir_out = "%s%s" % (self.root_out, self.header['version'])
        os.makedirs(self.dir_out, exist_ok=True)


        # Parse the rest of the document
        self.f_in.seek(self.header_limit)

        # Init the section dict
        section = {'content': ''}
        # Init the section flag
        F_sectionToBeWriten = False
        # Init the paragraph flag
        F_inP = False

        for line in self.f_in.readlines():
            p = self.parseLine(line)

            if p[0] == 'title':
                if len(p[1].group(1)) == 1:
                    # New section,
                    # write down the previous one
                    if F_sectionToBeWriten:
                        self.write_section(section)

                    # Reset the section
                    section = {'content': ''}

                    # Save its title in a buffer
                    section['name'] = p[1].group(2)

                    # Turn on the flag
                    F_sectionToBeWriten = True


            elif p[0] == 'meta':
                if p[1].group(1) == 'section_template':
                    section['template'] = p[1].group(3)

                if p[1].group(1) == 'section_url':
                    name = p[1].group(3)
                    # Add information about this section
                    section['url'] = p[1].group(3)
                    section['previous_url'] = self.pagination[name][0]
                    section['next_url'] = self.pagination[name][1]
                    section['percent'] = self.pagination[name][2]
                    # Get img for this sections
                    if name in self.imgRef['pictures']:
                        section['img'] = self.imgRef['pictures'][name]

                if p[1].group(1) == 'items':
                    section['items'] = [
                            self.items[i] for i in
                            p[1].group(3).split(", ")]


            else:
                if line == '\n' and F_inP:
                    section['content'] += '</p>\n'
                    F_inP = False

                elif line != '\n' and not F_inP:
                    section['content'] += '<p>\n'
                    F_inP = True

                section['content'] += line

        # Close the last paragraph, if necessary
        if F_inP:
            section['content'] += '</p>\n'
            F_inP = False


        # Write down the last section
        if F_sectionToBeWriten:
            self.write_section(section)

        # Write down the partsList
        section = {'name': 'partsList',
                    'template': 'partsList',
                    'url': 'partsList'}
        section['previous_url'] = self.pagination['partsList'][0]
        section['next_url'] = self.pagination['partsList'][1]
        section['percent'] = self.pagination['partsList'][2]
        section['items'] = self.header['items']
        self.write_section(section)

    def doPagination(self):
        """Do the pagination of the documentation.
        """

        # Start after the header
        self.f_in.seek(self.header_limit)

        # LIST SECTIONS
        # Init the sections buffer
        sections = []

        for line in self.f_in.readlines():
            if line[0] == '$':
                # ... it may be the section id
                re_meta = re.match(geoBuild.regex['meta'], line)
                if re_meta and re_meta.group(1) == 'section_url':
                    sections += [re_meta.group(3)]

        # PAGINATE
        # Pagination of the introduction
        self.pagination['intro'] = (
                '#', 'partsList', 0)

        # Pagination of the partList
        percent = int(100/len(sections))
        self.pagination['partsList'] = (
                'intro', sections[1], percent)

        # Pagination of the first section
        self.pagination[sections[1]] = (
                'partsList', sections[2], 2*percent)

        # Pagination of the last section
        self.pagination[sections[-1]] = (
                sections[-2], '#', 100)

        # Pagination of the rest
        for id, section in enumerate(sections[2:-1]):
            percent = int((id+2)*100/len(sections))
            self.pagination[section] = (sections[id-1+2],
                        sections[id+1+2], percent)



    # -------------
    # -- parsers --
    # -------------

    def parseLine(self, line):
        """Parse the line ie return the type of the line.
        """

        for r_name, r_express in geoBuild.regex.items():
            r_match = re.match(r_express, line)
            if r_match:
                return (r_name, r_match)

        return (None, None)


    # -------------
    # -- writers --
    # -------------

    def write_section(self, section):
        """Write down the section.
        """

        # Build the name of the file to be writen
        name_out = "%s/%s.html" % (self.dir_out, section['url'])

        # Load the template
        template = self.env.get_template(
                '%s.html' % section['template'])

        # Write the file
        with open(name_out, 'w') as f_out:
            f_out.write(template.render(section=section,
                header=self.header))


    def write_img(self, src, alt="", autoPath = True):
        if autoPath == True:
            src = self.img_path(src)
        return "<img src=\"%s\" alt=\"%s\" />" % (src, alt)

    def img_path(self, src):
        return "../i/doc/%s/%s" % (self.header['long_project_id'], src)

