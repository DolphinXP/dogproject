import {ComponentFixture, TestBed} from '@angular/core/testing';

import {LocationViewDialogComponent} from './location-view-dialog.component';

describe('LocationViewComponent', () => {
  let component: LocationViewDialogComponent;
  let fixture: ComponentFixture<LocationViewDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LocationViewDialogComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(LocationViewDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
