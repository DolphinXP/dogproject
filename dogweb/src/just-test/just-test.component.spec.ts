import { ComponentFixture, TestBed } from '@angular/core/testing';

import { JustTestComponent } from './just-test.component';

describe('JustTestComponent', () => {
  let component: JustTestComponent;
  let fixture: ComponentFixture<JustTestComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [JustTestComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(JustTestComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
